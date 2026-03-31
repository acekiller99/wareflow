import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="viewer")
    warehouse_access: list[str] = []


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    warehouse_access: list | None = []
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Warehouse ──
class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=20)
    address: str | None = None
    city: str | None = None
    country: str | None = None
    manager_name: str | None = None
    phone: str | None = None
    email: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    manager_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None


class WarehouseOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    address: str | None = None
    city: str | None = None
    country: str | None = None
    manager_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Location ──
class LocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    level: str = Field(pattern="^(zone|aisle|rack|shelf|bin)$")
    parent_id: uuid.UUID | None = None
    location_type: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    is_pickable: bool = True
    barcode: str | None = None
    sort_order: int = 0


class LocationUpdate(BaseModel):
    name: str | None = None
    location_type: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    is_pickable: bool | None = None
    is_active: bool | None = None
    barcode: str | None = None
    sort_order: int | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    code: str
    name: str
    level: str
    location_type: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    is_pickable: bool
    is_active: bool
    barcode: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


# ── Product Category ──
class ProductCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None
    description: str | None = None
    sort_order: int = 0


class ProductCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    description: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


# ── Product ──
class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category_id: uuid.UUID | None = None
    barcode: str | None = None
    unit_of_measure: str = Field(min_length=1, max_length=30)
    weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    cost_price: Decimal | None = None
    sell_price: Decimal | None = None
    min_stock_level: Decimal = Decimal("0")
    max_stock_level: Decimal | None = None
    reorder_quantity: Decimal | None = None
    is_batch_tracked: bool = False
    is_serial_tracked: bool = False
    is_perishable: bool = False
    storage_requirements: str | None = None
    image_url: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None
    barcode: str | None = None
    unit_of_measure: str | None = None
    weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    cost_price: Decimal | None = None
    sell_price: Decimal | None = None
    min_stock_level: Decimal | None = None
    max_stock_level: Decimal | None = None
    reorder_quantity: Decimal | None = None
    is_batch_tracked: bool | None = None
    is_serial_tracked: bool | None = None
    is_perishable: bool | None = None
    storage_requirements: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str | None = None
    category_id: uuid.UUID | None = None
    barcode: str | None = None
    unit_of_measure: str
    weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    cost_price: Decimal | None = None
    sell_price: Decimal | None = None
    min_stock_level: Decimal
    max_stock_level: Decimal | None = None
    reorder_quantity: Decimal | None = None
    is_batch_tracked: bool
    is_serial_tracked: bool
    is_perishable: bool
    storage_requirements: str | None = None
    image_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Supplier ──
class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    code: str | None = Field(default=None, max_length=20)
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_terms: str | None = None
    lead_time_days: int | None = None
    notes: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_terms: str | None = None
    lead_time_days: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_terms: str | None = None
    lead_time_days: int | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Inventory ──
class InventoryOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal | None = None
    batch_number: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    expiry_date: date | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjust(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    new_quantity: Decimal
    reason: str = Field(min_length=1)


# ── Purchase Order ──
class PurchaseOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity_ordered: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    notes: str | None = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    expected_delivery_date: date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    quantity_ordered: Decimal
    quantity_received: Decimal
    unit_cost: Decimal
    subtotal: Decimal
    notes: str | None = None

    model_config = {"from_attributes": True}


class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    po_number: str
    supplier_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    status: str
    order_date: date
    expected_delivery_date: date | None = None
    actual_delivery_date: date | None = None
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total: Decimal
    notes: str | None = None
    items: list[PurchaseOrderItemOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Goods Receipt ──
class GoodsReceiptItemCreate(BaseModel):
    product_id: uuid.UUID
    po_item_id: uuid.UUID | None = None
    quantity_received: Decimal = Field(gt=0)
    batch_number: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    expiry_date: date | None = None
    notes: str | None = None


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    notes: str | None = None
    items: list[GoodsReceiptItemCreate] = Field(min_length=1)


class GoodsReceiptItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    po_item_id: uuid.UUID | None = None
    quantity_received: Decimal
    quantity_accepted: Decimal | None = None
    quantity_rejected: Decimal
    put_away_location_id: uuid.UUID | None = None
    batch_number: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    expiry_date: date | None = None

    model_config = {"from_attributes": True}


class GoodsReceiptOut(BaseModel):
    id: uuid.UUID
    receipt_number: str
    purchase_order_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    status: str
    received_at: datetime
    notes: str | None = None
    items: list[GoodsReceiptItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PutAwayRequest(BaseModel):
    item_id: uuid.UUID
    location_id: uuid.UUID


class InspectItemRequest(BaseModel):
    item_id: uuid.UUID
    quantity_accepted: Decimal = Field(ge=0)
    quantity_rejected: Decimal = Field(ge=0, default=Decimal("0"))
    rejection_reason: str | None = None


# ── Sales Order ──
class SalesOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity_ordered: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    notes: str | None = None


class SalesOrderCreate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    shipping_address: str | None = None
    warehouse_id: uuid.UUID
    priority: str = "normal"
    required_date: date | None = None
    notes: str | None = None
    external_reference: str | None = None
    items: list[SalesOrderItemCreate] = Field(min_length=1)


class SalesOrderUpdate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    shipping_address: str | None = None
    priority: str | None = None
    required_date: date | None = None
    notes: str | None = None


class SalesOrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    quantity_ordered: Decimal
    quantity_allocated: Decimal
    quantity_picked: Decimal
    quantity_shipped: Decimal
    unit_price: Decimal
    subtotal: Decimal
    pick_location_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class SalesOrderOut(BaseModel):
    id: uuid.UUID
    so_number: str
    customer_name: str | None = None
    customer_email: str | None = None
    warehouse_id: uuid.UUID | None = None
    status: str
    priority: str
    order_date: date
    required_date: date | None = None
    shipped_date: date | None = None
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total: Decimal
    tracking_number: str | None = None
    shipping_carrier: str | None = None
    notes: str | None = None
    external_reference: str | None = None
    items: list[SalesOrderItemOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShipRequest(BaseModel):
    tracking_number: str | None = None
    shipping_carrier: str | None = None


# ── Pick List ──
class PickListItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    from_location_id: uuid.UUID | None = None
    quantity_to_pick: Decimal
    quantity_picked: Decimal
    status: str
    picked_at: datetime | None = None

    model_config = {"from_attributes": True}


class PickListOut(BaseModel):
    id: uuid.UUID
    pick_number: str
    warehouse_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    status: str
    pick_type: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items: list[PickListItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PickItemUpdate(BaseModel):
    quantity_picked: Decimal = Field(ge=0)
    status: str = Field(pattern="^(picked|short|skipped)$")


# ── Stock Transfer ──
class StockTransferItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    batch_number: str | None = None
    serial_number: str | None = None


class StockTransferCreate(BaseModel):
    from_warehouse_id: uuid.UUID | None = None
    to_warehouse_id: uuid.UUID | None = None
    from_location_id: uuid.UUID | None = None
    to_location_id: uuid.UUID | None = None
    reason: str | None = None
    items: list[StockTransferItemCreate] = Field(min_length=1)


class StockTransferItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    quantity: Decimal
    batch_number: str | None = None
    serial_number: str | None = None

    model_config = {"from_attributes": True}


class StockTransferOut(BaseModel):
    id: uuid.UUID
    transfer_number: str
    from_warehouse_id: uuid.UUID | None = None
    to_warehouse_id: uuid.UUID | None = None
    from_location_id: uuid.UUID | None = None
    to_location_id: uuid.UUID | None = None
    status: str
    reason: str | None = None
    items: list[StockTransferItemOut] = []
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Stock Count ──
class StockCountCreate(BaseModel):
    warehouse_id: uuid.UUID
    count_type: str = Field(pattern="^(full|cycle|spot)$")
    location_filter: dict | None = None
    product_filter: dict | None = None


class StockCountItemRecord(BaseModel):
    counted_quantity: Decimal = Field(ge=0)
    notes: str | None = None


class StockCountItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    system_quantity: Decimal
    counted_quantity: Decimal | None = None
    variance: Decimal | None = None
    batch_number: str | None = None
    notes: str | None = None
    counted_at: datetime | None = None

    model_config = {"from_attributes": True}


class StockCountOut(BaseModel):
    id: uuid.UUID
    count_number: str
    warehouse_id: uuid.UUID | None = None
    count_type: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items: list[StockCountItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Inventory Transaction ──
class InventoryTransactionOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    transaction_type: str
    quantity_change: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    batch_number: str | None = None
    serial_number: str | None = None
    notes: str | None = None
    performed_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
