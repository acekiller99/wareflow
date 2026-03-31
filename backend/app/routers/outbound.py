import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.models import (
    SalesOrder, SalesOrderItem, PickList, PickListItem,
    Inventory, InventoryTransaction, User,
)
from app.schemas.schemas import (
    SalesOrderCreate, SalesOrderOut, SalesOrderUpdate,
    PickListOut, PickItemUpdate, ShipRequest,
)

router = APIRouter(prefix="/api/v1", tags=["outbound"])


async def _next_so_number(db: AsyncSession) -> str:
    result = await db.execute(select(sa_func.count()).select_from(SalesOrder))
    count = result.scalar() or 0
    return f"SO-2026-{count + 1:05d}"


async def _next_pick_number(db: AsyncSession) -> str:
    result = await db.execute(select(sa_func.count()).select_from(PickList))
    count = result.scalar() or 0
    return f"PK-2026-{count + 1:05d}"


# ── Sales Orders ──
@router.get("/sales-orders", response_model=list[SalesOrderOut])
async def list_sales_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = select(SalesOrder).options(selectinload(SalesOrder.items))
    if status_filter:
        q = q.where(SalesOrder.status == status_filter)
    result = await db.execute(q.order_by(SalesOrder.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().unique().all()


@router.post("/sales-orders", response_model=SalesOrderOut, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    body: SalesOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    so_number = await _next_so_number(db)
    subtotal = sum(i.quantity_ordered * i.unit_price for i in body.items)
    so = SalesOrder(
        so_number=so_number,
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        shipping_address=body.shipping_address,
        warehouse_id=body.warehouse_id,
        priority=body.priority,
        required_date=body.required_date,
        notes=body.notes,
        external_reference=body.external_reference,
        subtotal=subtotal,
        total=subtotal,
        created_by=user.id,
    )
    db.add(so)
    await db.flush()

    for item in body.items:
        so_item = SalesOrderItem(
            sales_order_id=so.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            unit_price=item.unit_price,
            subtotal=item.quantity_ordered * item.unit_price,
        )
        db.add(so_item)

    await db.flush()
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so.id)
    )
    return result.scalar_one()


@router.get("/sales-orders/{so_id}", response_model=SalesOrderOut)
async def get_sales_order(
    so_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return so


@router.put("/sales-orders/{so_id}", response_model=SalesOrderOut)
async def update_sales_order(
    so_id: uuid.UUID,
    body: SalesOrderUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status != "pending":
        raise HTTPException(status_code=409, detail="Can only update pending orders")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(so, key, val)
    await db.flush()
    await db.refresh(so)
    return so


@router.post("/sales-orders/{so_id}/allocate", response_model=SalesOrderOut)
async def allocate_stock(
    so_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")

    for item in so.items:
        remaining = item.quantity_ordered - item.quantity_allocated
        if remaining <= 0:
            continue
        inv_result = await db.execute(
            select(Inventory)
            .where(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == so.warehouse_id,
            )
            .order_by(Inventory.expiry_date.asc().nulls_last())
        )
        for inv in inv_result.scalars().all():
            available = inv.quantity_on_hand - inv.quantity_reserved
            if available <= 0:
                continue
            alloc = min(available, remaining)
            inv.quantity_reserved += alloc
            item.quantity_allocated += alloc
            item.pick_location_id = inv.location_id
            remaining -= alloc
            if remaining <= 0:
                break

    so.status = "allocated"
    await db.flush()
    await db.refresh(so)
    return so


@router.post("/sales-orders/{so_id}/pick", response_model=PickListOut)
async def generate_pick_list(
    so_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status not in ("allocated",):
        raise HTTPException(status_code=409, detail="Order must be allocated first")

    pick_number = await _next_pick_number(db)
    pl = PickList(
        pick_number=pick_number,
        warehouse_id=so.warehouse_id,
        assigned_to=user.id,
    )
    db.add(pl)
    await db.flush()

    for item in so.items:
        if item.quantity_allocated > 0:
            pl_item = PickListItem(
                pick_list_id=pl.id,
                sales_order_item_id=item.id,
                product_id=item.product_id,
                from_location_id=item.pick_location_id,
                quantity_to_pick=item.quantity_allocated,
            )
            db.add(pl_item)

    so.status = "picking"
    await db.flush()
    result = await db.execute(
        select(PickList).options(selectinload(PickList.items)).where(PickList.id == pl.id)
    )
    return result.scalar_one()


@router.post("/sales-orders/{so_id}/pack", response_model=SalesOrderOut)
async def pack_order(
    so_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status not in ("picked", "picking"):
        raise HTTPException(status_code=409, detail="Order is not ready for packing")
    so.status = "packed"
    await db.flush()
    await db.refresh(so)
    return so


@router.post("/sales-orders/{so_id}/ship", response_model=SalesOrderOut)
async def ship_order(
    so_id: uuid.UUID,
    body: ShipRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status != "packed":
        raise HTTPException(status_code=409, detail="Order must be packed first")
    so.status = "shipped"
    so.shipped_date = date.today()
    so.tracking_number = body.tracking_number
    so.shipping_carrier = body.shipping_carrier

    # Deduct inventory and release reserved
    for item in so.items:
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.location_id == item.pick_location_id,
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv:
            old_qty = inv.quantity_on_hand
            inv.quantity_on_hand -= item.quantity_shipped or item.quantity_allocated
            inv.quantity_reserved -= item.quantity_allocated
            item.quantity_shipped = item.quantity_allocated

            txn = InventoryTransaction(
                product_id=item.product_id,
                warehouse_id=so.warehouse_id,
                location_id=item.pick_location_id,
                transaction_type="ship",
                quantity_change=-(item.quantity_shipped),
                quantity_before=old_qty,
                quantity_after=inv.quantity_on_hand,
                reference_type="sales_order",
                reference_id=so.id,
                performed_by=user.id,
            )
            db.add(txn)

    await db.flush()
    await db.refresh(so)
    return so


@router.post("/sales-orders/{so_id}/cancel", response_model=SalesOrderOut)
async def cancel_order(
    so_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status in ("shipped", "delivered"):
        raise HTTPException(status_code=409, detail="Cannot cancel shipped/delivered orders")

    # Release reserved stock
    for item in so.items:
        if item.quantity_allocated > 0 and item.pick_location_id:
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.location_id == item.pick_location_id,
                )
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                inv.quantity_reserved -= item.quantity_allocated

    so.status = "cancelled"
    await db.flush()
    await db.refresh(so)
    return so


# ── Pick Lists ──
@router.get("/pick-lists", response_model=list[PickListOut])
async def list_pick_lists(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
):
    q = select(PickList).options(selectinload(PickList.items))
    if status_filter:
        q = q.where(PickList.status == status_filter)
    result = await db.execute(q.order_by(PickList.created_at.desc()))
    return result.scalars().unique().all()


@router.get("/pick-lists/{pl_id}", response_model=PickListOut)
async def get_pick_list(
    pl_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PickList).options(selectinload(PickList.items)).where(PickList.id == pl_id)
    )
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Pick list not found")
    return pl


@router.post("/pick-lists/{pl_id}/start", response_model=PickListOut)
async def start_pick(
    pl_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PickList).options(selectinload(PickList.items)).where(PickList.id == pl_id)
    )
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Pick list not found")
    pl.status = "in_progress"
    pl.started_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(pl)
    return pl


@router.put("/pick-lists/{pl_id}/items/{item_id}", response_model=PickListOut)
async def update_pick_item(
    pl_id: uuid.UUID,
    item_id: uuid.UUID,
    body: PickItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PickListItem).where(PickListItem.id == item_id, PickListItem.pick_list_id == pl_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Pick item not found")
    item.quantity_picked = body.quantity_picked
    item.status = body.status
    item.picked_at = datetime.now(timezone.utc)
    await db.flush()

    result = await db.execute(
        select(PickList).options(selectinload(PickList.items)).where(PickList.id == pl_id)
    )
    return result.scalar_one()


@router.post("/pick-lists/{pl_id}/complete", response_model=PickListOut)
async def complete_pick(
    pl_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PickList).options(selectinload(PickList.items)).where(PickList.id == pl_id)
    )
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Pick list not found")
    pl.status = "completed"
    pl.completed_at = datetime.now(timezone.utc)

    # Update SO items with picked quantities
    for item in pl.items:
        if item.sales_order_item_id:
            soi_result = await db.execute(
                select(SalesOrderItem).where(SalesOrderItem.id == item.sales_order_item_id)
            )
            soi = soi_result.scalar_one_or_none()
            if soi:
                soi.quantity_picked = item.quantity_picked

    await db.flush()
    await db.refresh(pl)
    return pl
