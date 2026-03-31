import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.models import (
    StockCount, StockCountItem, Inventory, InventoryTransaction, User,
)
from app.schemas.schemas import (
    StockCountCreate, StockCountOut, StockCountItemRecord, StockCountItemOut,
)

router = APIRouter(prefix="/api/v1/stock-counts", tags=["stock-counts"])


async def _next_count_number(db: AsyncSession) -> str:
    result = await db.execute(select(sa_func.count()).select_from(StockCount))
    count = result.scalar() or 0
    return f"SC-2026-{count + 1:05d}"


@router.get("", response_model=list[StockCountOut])
async def list_stock_counts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockCount)
        .options(selectinload(StockCount.items))
        .order_by(StockCount.created_at.desc())
    )
    return result.scalars().unique().all()


@router.post("", response_model=StockCountOut, status_code=status.HTTP_201_CREATED)
async def create_stock_count(
    body: StockCountCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    number = await _next_count_number(db)
    sc = StockCount(
        count_number=number,
        warehouse_id=body.warehouse_id,
        count_type=body.count_type,
        location_filter=body.location_filter,
        product_filter=body.product_filter,
        created_by=user.id,
    )
    db.add(sc)
    await db.flush()

    # Populate count items from current inventory
    q = select(Inventory).where(Inventory.warehouse_id == body.warehouse_id)
    inv_result = await db.execute(q)
    for inv in inv_result.scalars().all():
        item = StockCountItem(
            stock_count_id=sc.id,
            product_id=inv.product_id,
            location_id=inv.location_id,
            system_quantity=inv.quantity_on_hand,
            batch_number=inv.batch_number,
        )
        db.add(item)

    await db.flush()
    result = await db.execute(
        select(StockCount).options(selectinload(StockCount.items)).where(StockCount.id == sc.id)
    )
    return result.scalar_one()


@router.post("/{sc_id}/start", response_model=StockCountOut)
async def start_stock_count(
    sc_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockCount).options(selectinload(StockCount.items)).where(StockCount.id == sc_id)
    )
    sc = result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Stock count not found")
    if sc.status != "planned":
        raise HTTPException(status_code=409, detail="Count has already started")
    sc.status = "in_progress"
    sc.started_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(sc)
    return sc


@router.put("/{sc_id}/items/{item_id}", response_model=StockCountItemOut)
async def record_count(
    sc_id: uuid.UUID,
    item_id: uuid.UUID,
    body: StockCountItemRecord,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockCountItem).where(
            StockCountItem.id == item_id,
            StockCountItem.stock_count_id == sc_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Count item not found")
    item.counted_quantity = body.counted_quantity
    item.variance = body.counted_quantity - item.system_quantity
    item.notes = body.notes
    item.counted_by = user.id
    item.counted_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(item)
    return item


@router.post("/{sc_id}/complete", response_model=StockCountOut)
async def complete_stock_count(
    sc_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockCount).options(selectinload(StockCount.items)).where(StockCount.id == sc_id)
    )
    sc = result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Stock count not found")
    if sc.status != "in_progress":
        raise HTTPException(status_code=409, detail="Count must be in progress")

    # Apply adjustments
    for item in sc.items:
        if item.counted_quantity is not None and item.variance and item.variance != 0:
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == item.product_id,
                    Inventory.location_id == item.location_id,
                )
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                old_qty = inv.quantity_on_hand
                inv.quantity_on_hand = item.counted_quantity
                inv.last_counted_at = datetime.now(timezone.utc)
                txn = InventoryTransaction(
                    product_id=item.product_id,
                    warehouse_id=sc.warehouse_id,
                    location_id=item.location_id,
                    transaction_type="count",
                    quantity_change=item.variance,
                    quantity_before=old_qty,
                    quantity_after=item.counted_quantity,
                    reference_type="stock_count",
                    reference_id=sc.id,
                    notes=item.notes,
                    performed_by=user.id,
                )
                db.add(txn)

    sc.status = "completed"
    sc.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(sc)
    return sc


@router.get("/{sc_id}/variance", response_model=list[StockCountItemOut])
async def variance_report(
    sc_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(StockCountItem).where(
            StockCountItem.stock_count_id == sc_id,
            StockCountItem.variance.isnot(None),
            StockCountItem.variance != 0,
        )
    )
    return result.scalars().all()
