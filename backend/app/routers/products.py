import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Product, ProductCategory, User, Inventory, InventoryTransaction
from app.schemas.schemas import (
    ProductCategoryCreate, ProductCategoryOut,
    ProductCreate, ProductOut, ProductUpdate,
    InventoryOut, InventoryTransactionOut,
)

router = APIRouter(prefix="/api/v1", tags=["products"])


# ── Product Categories ──
@router.get("/product-categories", response_model=list[ProductCategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(ProductCategory).order_by(ProductCategory.sort_order, ProductCategory.name))
    return result.scalars().all()


@router.post("/product-categories", response_model=ProductCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: ProductCategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    cat = ProductCategory(**body.model_dump())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


# ── Products ──
@router.get("/products", response_model=list[ProductOut])
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = select(Product)
    if search:
        q = q.where(or_(
            Product.name.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%"),
            Product.barcode.ilike(f"%{search}%"),
        ))
    if category_id:
        q = q.where(Product.category_id == category_id)
    if is_active is not None:
        q = q.where(Product.is_active == is_active)
    result = await db.execute(q.order_by(Product.name).offset(offset).limit(limit))
    return result.scalars().all()


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    existing = await db.execute(select(Product).where(Product.sku == body.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="SKU already exists")
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(product, key, val)
    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    await db.flush()


@router.get("/products/{product_id}/inventory", response_model=list[InventoryOut])
async def product_inventory(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Inventory).where(Inventory.product_id == product_id)
    )
    return result.scalars().all()


@router.get("/products/{product_id}/transactions", response_model=list[InventoryTransactionOut])
async def product_transactions(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
):
    result = await db.execute(
        select(InventoryTransaction)
        .where(InventoryTransaction.product_id == product_id)
        .order_by(InventoryTransaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/products/scan/{barcode}", response_model=ProductOut)
async def scan_product(
    barcode: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found for barcode")
    return product
