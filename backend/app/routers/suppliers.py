import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Supplier, ProductSupplier, Product, PurchaseOrder, User
from app.schemas.schemas import SupplierCreate, SupplierOut, SupplierUpdate, ProductOut, PurchaseOrderOut

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: bool | None = None,
):
    q = select(Supplier)
    if is_active is not None:
        q = q.where(Supplier.is_active == is_active)
    result = await db.execute(q.order_by(Supplier.name))
    return result.scalars().all()


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    if body.code:
        existing = await db.execute(select(Supplier).where(Supplier.code == body.code))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Supplier code already exists")
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(supplier, key, val)
    await db.flush()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}/products", response_model=list[ProductOut])
async def supplier_products(
    supplier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Product)
        .join(ProductSupplier, ProductSupplier.product_id == Product.id)
        .where(ProductSupplier.supplier_id == supplier_id)
    )
    return result.scalars().all()


@router.get("/{supplier_id}/purchase-orders", response_model=list[PurchaseOrderOut])
async def supplier_purchase_orders(
    supplier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.supplier_id == supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
    )
    return result.scalars().all()
