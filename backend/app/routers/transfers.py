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
    StockTransfer, StockTransferItem, Inventory, InventoryTransaction, User,
)
from app.schemas.schemas import StockTransferCreate, StockTransferOut

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])


async def _next_transfer_number(db: AsyncSession) -> str:
    result = await db.execute(select(sa_func.count()).select_from(StockTransfer))
    count = result.scalar() or 0
    return f"TR-2026-{count + 1:05d}"


@router.get("", response_model=list[StockTransferOut])
async def list_transfers(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
):
    q = select(StockTransfer).options(selectinload(StockTransfer.items))
    if status_filter:
        q = q.where(StockTransfer.status == status_filter)
    result = await db.execute(q.order_by(StockTransfer.created_at.desc()))
    return result.scalars().unique().all()


@router.post("", response_model=StockTransferOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: StockTransferCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    number = await _next_transfer_number(db)
    transfer = StockTransfer(
        transfer_number=number,
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        reason=body.reason,
        initiated_by=user.id,
    )
    db.add(transfer)
    await db.flush()

    for item in body.items:
        ti = StockTransferItem(
            transfer_id=transfer.id,
            product_id=item.product_id,
            quantity=item.quantity,
            batch_number=item.batch_number,
            serial_number=item.serial_number,
        )
        db.add(ti)

    await db.flush()
    result = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer.id)
    )
    return result.scalar_one()


@router.put("/{transfer_id}", response_model=StockTransferOut)
async def update_transfer(
    transfer_id: uuid.UUID,
    body: StockTransferCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != "draft":
        raise HTTPException(status_code=409, detail="Can only update draft transfers")
    transfer.from_warehouse_id = body.from_warehouse_id
    transfer.to_warehouse_id = body.to_warehouse_id
    transfer.from_location_id = body.from_location_id
    transfer.to_location_id = body.to_location_id
    transfer.reason = body.reason
    for item in transfer.items:
        await db.delete(item)
    for item in body.items:
        ti = StockTransferItem(
            transfer_id=transfer.id,
            product_id=item.product_id,
            quantity=item.quantity,
            batch_number=item.batch_number,
            serial_number=item.serial_number,
        )
        db.add(ti)
    await db.flush()
    result = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer.id)
    )
    return result.scalar_one()


@router.post("/{transfer_id}/dispatch", response_model=StockTransferOut)
async def dispatch_transfer(
    transfer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != "draft":
        raise HTTPException(status_code=409, detail="Can only dispatch draft transfers")

    # Deduct from source
    for item in transfer.items:
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.location_id == transfer.from_location_id,
            )
        )
        inv = inv_result.scalar_one_or_none()
        if not inv or inv.quantity_on_hand < item.quantity:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for product {item.product_id}")
        old_qty = inv.quantity_on_hand
        inv.quantity_on_hand -= item.quantity
        txn = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=transfer.from_warehouse_id,
            location_id=transfer.from_location_id,
            transaction_type="transfer_out",
            quantity_change=-item.quantity,
            quantity_before=old_qty,
            quantity_after=inv.quantity_on_hand,
            reference_type="transfer",
            reference_id=transfer.id,
            performed_by=user.id,
        )
        db.add(txn)

    transfer.status = "in_transit"
    await db.flush()
    await db.refresh(transfer)
    return transfer


@router.post("/{transfer_id}/receive", response_model=StockTransferOut)
async def receive_transfer(
    transfer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != "in_transit":
        raise HTTPException(status_code=409, detail="Transfer is not in transit")

    for item in transfer.items:
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.location_id == transfer.to_location_id,
            )
        )
        inv = inv_result.scalar_one_or_none()
        old_qty = Decimal("0")
        if inv:
            old_qty = inv.quantity_on_hand
            inv.quantity_on_hand += item.quantity
        else:
            inv = Inventory(
                product_id=item.product_id,
                location_id=transfer.to_location_id,
                warehouse_id=transfer.to_warehouse_id,
                quantity_on_hand=item.quantity,
                batch_number=item.batch_number,
                serial_number=item.serial_number,
            )
            db.add(inv)
        txn = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=transfer.to_warehouse_id,
            location_id=transfer.to_location_id,
            transaction_type="transfer_in",
            quantity_change=item.quantity,
            quantity_before=old_qty,
            quantity_after=old_qty + item.quantity,
            reference_type="transfer",
            reference_id=transfer.id,
            performed_by=user.id,
        )
        db.add(txn)

    transfer.status = "received"
    transfer.received_by = user.id
    transfer.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(transfer)
    return transfer
