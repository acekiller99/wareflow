import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.models import (
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Inventory, InventoryTransaction, Location, User,
)
from app.schemas.schemas import (
    PurchaseOrderCreate, PurchaseOrderOut,
    GoodsReceiptCreate, GoodsReceiptOut, GoodsReceiptItemOut,
    InspectItemRequest, PutAwayRequest,
)

router = APIRouter(prefix="/api/v1", tags=["inbound"])


async def _next_po_number(db: AsyncSession) -> str:
    result = await db.execute(
        select(sa_func.count()).select_from(PurchaseOrder)
    )
    count = result.scalar() or 0
    return f"PO-2026-{count + 1:05d}"


async def _next_gr_number(db: AsyncSession) -> str:
    result = await db.execute(
        select(sa_func.count()).select_from(GoodsReceipt)
    )
    count = result.scalar() or 0
    return f"GR-2026-{count + 1:05d}"


# ── Purchase Orders ──
@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
async def list_purchase_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
    if status_filter:
        q = q.where(PurchaseOrder.status == status_filter)
    result = await db.execute(q.order_by(PurchaseOrder.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().unique().all()


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    po_number = await _next_po_number(db)
    subtotal = sum(item.quantity_ordered * item.unit_cost for item in body.items)
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=body.supplier_id,
        warehouse_id=body.warehouse_id,
        expected_delivery_date=body.expected_delivery_date,
        notes=body.notes,
        subtotal=subtotal,
        total=subtotal,
        created_by=user.id,
    )
    db.add(po)
    await db.flush()

    for item in body.items:
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=item.unit_cost,
            subtotal=item.quantity_ordered * item.unit_cost,
        )
        db.add(po_item)

    await db.flush()
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po.id)
    )
    return result.scalar_one()


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
async def get_purchase_order(
    po_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.put("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
async def update_purchase_order(
    po_id: uuid.UUID,
    body: PurchaseOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "draft":
        raise HTTPException(status_code=409, detail="Can only update draft POs")
    po.supplier_id = body.supplier_id
    po.warehouse_id = body.warehouse_id
    po.expected_delivery_date = body.expected_delivery_date
    po.notes = body.notes
    # Remove old items
    for item in po.items:
        await db.delete(item)
    subtotal = Decimal("0")
    for item in body.items:
        sub = item.quantity_ordered * item.unit_cost
        subtotal += sub
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=item.unit_cost,
            subtotal=sub,
        )
        db.add(po_item)
    po.subtotal = subtotal
    po.total = subtotal
    await db.flush()
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po.id)
    )
    return result.scalar_one()


@router.post("/purchase-orders/{po_id}/submit", response_model=PurchaseOrderOut)
async def submit_po(
    po_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "draft":
        raise HTTPException(status_code=409, detail="PO is not in draft status")
    po.status = "submitted"
    await db.flush()
    await db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/cancel", response_model=PurchaseOrderOut)
async def cancel_po(
    po_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status in ("received", "cancelled"):
        raise HTTPException(status_code=409, detail="Cannot cancel this PO")
    po.status = "cancelled"
    await db.flush()
    await db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/receive", response_model=GoodsReceiptOut)
async def receive_po(
    po_id: uuid.UUID,
    body: GoodsReceiptCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    gr_number = await _next_gr_number(db)
    gr = GoodsReceipt(
        receipt_number=gr_number,
        purchase_order_id=po_id,
        warehouse_id=body.warehouse_id,
        supplier_id=po.supplier_id,
        received_by=user.id,
        notes=body.notes,
    )
    db.add(gr)
    await db.flush()

    for item in body.items:
        gr_item = GoodsReceiptItem(
            goods_receipt_id=gr.id,
            product_id=item.product_id,
            po_item_id=item.po_item_id,
            quantity_received=item.quantity_received,
            quantity_accepted=item.quantity_received,
            batch_number=item.batch_number,
            lot_number=item.lot_number,
            serial_number=item.serial_number,
            expiry_date=item.expiry_date,
        )
        db.add(gr_item)

        # Update PO item received qty
        if item.po_item_id:
            poi_result = await db.execute(
                select(PurchaseOrderItem).where(PurchaseOrderItem.id == item.po_item_id)
            )
            poi = poi_result.scalar_one_or_none()
            if poi:
                poi.quantity_received += item.quantity_received

    # Update PO status
    all_received = all(i.quantity_received >= i.quantity_ordered for i in po.items)
    po.status = "received" if all_received else "partially_received"

    await db.flush()
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr.id)
    )
    return result.scalar_one()


@router.get("/purchase-orders/{po_id}/receipts", response_model=list[GoodsReceiptOut])
async def po_receipts(
    po_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.items))
        .where(GoodsReceipt.purchase_order_id == po_id)
    )
    return result.scalars().unique().all()


# ── Goods Receipts ──
@router.post("/goods-receipts", response_model=GoodsReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_goods_receipt(
    body: GoodsReceiptCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    gr_number = await _next_gr_number(db)
    gr = GoodsReceipt(
        receipt_number=gr_number,
        purchase_order_id=body.purchase_order_id,
        warehouse_id=body.warehouse_id,
        supplier_id=body.supplier_id,
        received_by=user.id,
        notes=body.notes,
    )
    db.add(gr)
    await db.flush()

    for item in body.items:
        gr_item = GoodsReceiptItem(
            goods_receipt_id=gr.id,
            product_id=item.product_id,
            po_item_id=item.po_item_id,
            quantity_received=item.quantity_received,
            quantity_accepted=item.quantity_received,
            batch_number=item.batch_number,
            lot_number=item.lot_number,
            serial_number=item.serial_number,
            expiry_date=item.expiry_date,
        )
        db.add(gr_item)

    await db.flush()
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr.id)
    )
    return result.scalar_one()


@router.get("/goods-receipts/{gr_id}", response_model=GoodsReceiptOut)
async def get_goods_receipt(
    gr_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr_id)
    )
    gr = result.scalar_one_or_none()
    if not gr:
        raise HTTPException(status_code=404, detail="Goods receipt not found")
    return gr


@router.put("/goods-receipts/{gr_id}/inspect", response_model=GoodsReceiptOut)
async def inspect_goods(
    gr_id: uuid.UUID,
    body: list[InspectItemRequest],
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr_id)
    )
    gr = result.scalar_one_or_none()
    if not gr:
        raise HTTPException(status_code=404, detail="Goods receipt not found")

    for inspection in body:
        item_result = await db.execute(
            select(GoodsReceiptItem).where(GoodsReceiptItem.id == inspection.item_id)
        )
        item = item_result.scalar_one_or_none()
        if item:
            item.quantity_accepted = inspection.quantity_accepted
            item.quantity_rejected = inspection.quantity_rejected
            item.rejection_reason = inspection.rejection_reason

    gr.status = "inspecting"
    await db.flush()
    await db.refresh(gr)
    return gr


@router.post("/goods-receipts/{gr_id}/put-away", response_model=GoodsReceiptOut)
async def put_away(
    gr_id: uuid.UUID,
    body: list[PutAwayRequest],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr_id)
    )
    gr = result.scalar_one_or_none()
    if not gr:
        raise HTTPException(status_code=404, detail="Goods receipt not found")

    for pa in body:
        item_result = await db.execute(
            select(GoodsReceiptItem).where(GoodsReceiptItem.id == pa.item_id)
        )
        item = item_result.scalar_one_or_none()
        if item:
            item.put_away_location_id = pa.location_id
            qty = item.quantity_accepted or item.quantity_received

            # Update inventory
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.location_id == pa.location_id,
                )
            )
            inv = inv_result.scalar_one_or_none()
            old_qty = Decimal("0")
            if inv:
                old_qty = inv.quantity_on_hand
                inv.quantity_on_hand += qty
            else:
                inv = Inventory(
                    product_id=item.product_id,
                    location_id=pa.location_id,
                    warehouse_id=gr.warehouse_id,
                    quantity_on_hand=qty,
                    batch_number=item.batch_number,
                    lot_number=item.lot_number,
                    serial_number=item.serial_number,
                    expiry_date=item.expiry_date,
                )
                db.add(inv)

            # Transaction
            txn = InventoryTransaction(
                product_id=item.product_id,
                warehouse_id=gr.warehouse_id,
                location_id=pa.location_id,
                transaction_type="put_away",
                quantity_change=qty,
                quantity_before=old_qty,
                quantity_after=old_qty + qty,
                reference_type="goods_receipt",
                reference_id=gr.id,
                batch_number=item.batch_number,
                serial_number=item.serial_number,
                performed_by=user.id,
            )
            db.add(txn)

    gr.status = "put_away"
    await db.flush()
    await db.refresh(gr)
    return gr


@router.post("/goods-receipts/{gr_id}/complete", response_model=GoodsReceiptOut)
async def complete_receipt(
    gr_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(GoodsReceipt).options(selectinload(GoodsReceipt.items)).where(GoodsReceipt.id == gr_id)
    )
    gr = result.scalar_one_or_none()
    if not gr:
        raise HTTPException(status_code=404, detail="Goods receipt not found")
    gr.status = "completed"
    await db.flush()
    await db.refresh(gr)
    return gr
