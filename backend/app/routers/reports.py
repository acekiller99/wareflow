from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Inventory, Product, InventoryTransaction, User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/stock-summary")
async def stock_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    warehouse_id: str | None = None,
):
    q = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            sa_func.sum(Inventory.quantity_on_hand).label("total_on_hand"),
            sa_func.sum(Inventory.quantity_reserved).label("total_reserved"),
            sa_func.sum(Inventory.quantity_on_hand - Inventory.quantity_reserved).label("total_available"),
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.id, Product.sku, Product.name)
    )
    if warehouse_id:
        q = q.where(Inventory.warehouse_id == warehouse_id)
    result = await db.execute(q.order_by(Product.name))
    rows = result.all()
    return [
        {
            "product_id": str(r[0]),
            "sku": r[1],
            "name": r[2],
            "total_on_hand": float(r[3] or 0),
            "total_reserved": float(r[4] or 0),
            "total_available": float(r[5] or 0),
        }
        for r in rows
    ]


@router.get("/low-stock")
async def low_stock_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    q = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            Product.min_stock_level,
            sa_func.sum(Inventory.quantity_on_hand).label("total_on_hand"),
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.id, Product.sku, Product.name, Product.min_stock_level)
        .having(sa_func.sum(Inventory.quantity_on_hand) < Product.min_stock_level)
    )
    result = await db.execute(q.order_by(Product.name))
    rows = result.all()
    return [
        {
            "product_id": str(r[0]),
            "sku": r[1],
            "name": r[2],
            "min_stock_level": float(r[3] or 0),
            "total_on_hand": float(r[4] or 0),
            "deficit": float((r[3] or 0) - (r[4] or 0)),
        }
        for r in rows
    ]


@router.get("/reorder-suggestions")
async def reorder_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    q = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            Product.min_stock_level,
            Product.reorder_quantity,
            sa_func.sum(Inventory.quantity_on_hand).label("total_on_hand"),
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.id, Product.sku, Product.name, Product.min_stock_level, Product.reorder_quantity)
        .having(sa_func.sum(Inventory.quantity_on_hand) < Product.min_stock_level)
    )
    result = await db.execute(q.order_by(Product.name))
    rows = result.all()
    return [
        {
            "product_id": str(r[0]),
            "sku": r[1],
            "name": r[2],
            "min_stock_level": float(r[3] or 0),
            "reorder_quantity": float(r[4] or 0),
            "current_stock": float(r[5] or 0),
        }
        for r in rows
    ]


@router.get("/expiry-forecast")
async def expiry_forecast(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    days: int = Query(default=90, ge=1),
):
    from datetime import date, timedelta
    cutoff = date.today() + timedelta(days=days)
    result = await db.execute(
        select(
            Inventory.id,
            Product.sku,
            Product.name,
            Inventory.quantity_on_hand,
            Inventory.expiry_date,
            Inventory.batch_number,
        )
        .join(Product, Product.id == Inventory.product_id)
        .where(Inventory.expiry_date.isnot(None))
        .where(Inventory.expiry_date <= cutoff)
        .where(Inventory.quantity_on_hand > 0)
        .order_by(Inventory.expiry_date)
    )
    rows = result.all()
    return [
        {
            "inventory_id": str(r[0]),
            "sku": r[1],
            "name": r[2],
            "quantity": float(r[3]),
            "expiry_date": r[4].isoformat(),
            "batch_number": r[5],
        }
        for r in rows
    ]


@router.get("/movement-history")
async def movement_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    warehouse_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    q = (
        select(
            InventoryTransaction.id,
            InventoryTransaction.transaction_type,
            Product.sku,
            Product.name,
            InventoryTransaction.quantity_change,
            InventoryTransaction.quantity_before,
            InventoryTransaction.quantity_after,
            InventoryTransaction.reference_type,
            InventoryTransaction.created_at,
        )
        .join(Product, Product.id == InventoryTransaction.product_id)
    )
    if warehouse_id:
        q = q.where(InventoryTransaction.warehouse_id == warehouse_id)
    result = await db.execute(q.order_by(InventoryTransaction.created_at.desc()).limit(limit))
    rows = result.all()
    return [
        {
            "id": str(r[0]),
            "transaction_type": r[1],
            "sku": r[2],
            "product_name": r[3],
            "quantity_change": float(r[4]),
            "quantity_before": float(r[5]),
            "quantity_after": float(r[6]),
            "reference_type": r[7],
            "created_at": r[8].isoformat(),
        }
        for r in rows
    ]
