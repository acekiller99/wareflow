import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Inventory, InventoryTransaction, Product, Location, User
from app.schemas.schemas import (
    InventoryAdjust, InventoryOut, InventoryTransactionOut,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryOut])
async def list_inventory(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    warehouse_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = select(Inventory)
    if warehouse_id:
        q = q.where(Inventory.warehouse_id == warehouse_id)
    if product_id:
        q = q.where(Inventory.product_id == product_id)
    result = await db.execute(q.offset(offset).limit(limit))
    return result.scalars().all()


@router.get("/low-stock", response_model=list[InventoryOut])
async def low_stock(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    # products where total on-hand < min stock level
    from sqlalchemy import func as sa_func
    subq = (
        select(
            Inventory.product_id,
            sa_func.sum(Inventory.quantity_on_hand).label("total_on_hand"),
        )
        .group_by(Inventory.product_id)
        .subquery()
    )
    result = await db.execute(
        select(Inventory)
        .join(Product, Product.id == Inventory.product_id)
        .join(subq, subq.c.product_id == Inventory.product_id)
        .where(subq.c.total_on_hand < Product.min_stock_level)
    )
    return result.scalars().all()


@router.get("/expiring", response_model=list[InventoryOut])
async def expiring_stock(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    days: int = Query(default=30, ge=1),
):
    from datetime import date, timedelta
    cutoff = date.today() + timedelta(days=days)
    result = await db.execute(
        select(Inventory)
        .where(Inventory.expiry_date.isnot(None))
        .where(Inventory.expiry_date <= cutoff)
        .where(Inventory.quantity_on_hand > 0)
        .order_by(Inventory.expiry_date)
    )
    return result.scalars().all()


@router.post("/adjust", response_model=InventoryOut)
async def adjust_stock(
    body: InventoryAdjust,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == body.product_id,
            Inventory.location_id == body.location_id,
        )
    )
    inv = result.scalar_one_or_none()

    # Get location for warehouse_id
    loc_result = await db.execute(select(Location).where(Location.id == body.location_id))
    loc = loc_result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    old_qty = Decimal("0")
    if inv:
        old_qty = inv.quantity_on_hand
        inv.quantity_on_hand = body.new_quantity
    else:
        inv = Inventory(
            product_id=body.product_id,
            location_id=body.location_id,
            warehouse_id=loc.warehouse_id,
            quantity_on_hand=body.new_quantity,
        )
        db.add(inv)

    # Record transaction
    txn = InventoryTransaction(
        product_id=body.product_id,
        warehouse_id=loc.warehouse_id,
        location_id=body.location_id,
        transaction_type="adjustment",
        quantity_change=body.new_quantity - old_qty,
        quantity_before=old_qty,
        quantity_after=body.new_quantity,
        notes=body.reason,
        performed_by=user.id,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(inv)
    return inv


@router.get("/transactions", response_model=list[InventoryTransactionOut])
async def list_transactions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    warehouse_id: uuid.UUID | None = None,
    transaction_type: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = select(InventoryTransaction)
    if warehouse_id:
        q = q.where(InventoryTransaction.warehouse_id == warehouse_id)
    if transaction_type:
        q = q.where(InventoryTransaction.transaction_type == transaction_type)
    result = await db.execute(q.order_by(InventoryTransaction.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().all()
