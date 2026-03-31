import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Location, User, Warehouse, Inventory
from app.schemas.schemas import (
    LocationCreate, LocationOut, LocationUpdate,
    WarehouseCreate, WarehouseOut, WarehouseUpdate, InventoryOut,
)

router = APIRouter(prefix="/api/v1", tags=["warehouses"])


# ── Warehouses ──
@router.get("/warehouses", response_model=list[WarehouseOut])
async def list_warehouses(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: bool | None = None,
):
    q = select(Warehouse)
    if is_active is not None:
        q = q.where(Warehouse.is_active == is_active)
    result = await db.execute(q.order_by(Warehouse.name))
    return result.scalars().all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    existing = await db.execute(select(Warehouse).where(Warehouse.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Warehouse code already exists")
    wh = Warehouse(**body.model_dump())
    db.add(wh)
    await db.flush()
    await db.refresh(wh)
    return wh


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseOut)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    body: WarehouseUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(wh, key, val)
    await db.flush()
    await db.refresh(wh)
    return wh


# ── Locations ──
@router.get("/warehouses/{warehouse_id}/locations", response_model=list[LocationOut])
async def list_locations(
    warehouse_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Location)
        .where(Location.warehouse_id == warehouse_id)
        .order_by(Location.sort_order, Location.code)
    )
    return result.scalars().all()


@router.post("/warehouses/{warehouse_id}/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(
    warehouse_id: uuid.UUID,
    body: LocationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    # verify warehouse exists
    wh = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    if not wh.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Warehouse not found")
    loc = Location(warehouse_id=warehouse_id, **body.model_dump())
    db.add(loc)
    await db.flush()
    await db.refresh(loc)
    return loc


@router.put("/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(loc, key, val)
    await db.flush()
    await db.refresh(loc)
    return loc


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    # check for inventory
    inv = await db.execute(
        select(Inventory).where(Inventory.location_id == location_id).limit(1)
    )
    if inv.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cannot delete location with existing inventory")
    await db.delete(loc)


@router.get("/locations/{location_id}/inventory", response_model=list[InventoryOut])
async def location_inventory(
    location_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Inventory).where(Inventory.location_id == location_id)
    )
    return result.scalars().all()


@router.post("/locations/scan/{barcode}", response_model=LocationOut)
async def scan_location(
    barcode: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Location).where(Location.barcode == barcode))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found for barcode")
    return loc
