# WareFlow — Warehouse Management System (WMS)

## Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | WareFlow |
| **Code** | `wareflow` |
| **Domain** | Warehouse & Inventory Management |
| **Type** | Full-stack web application with mobile-friendly UI |
| **Primary Language** | Python (FastAPI) + TypeScript (Next.js) |
| **License** | MIT |

---

## 1. Project Overview

WareFlow is a self-hosted warehouse management system that handles:
- **Inbound/Outbound management** — receiving, put-away, picking, packing, shipping
- **Inventory tracking** — real-time stock levels across multiple warehouses/zones
- **Barcode/QR scanning** — mobile-friendly scan for all operations
- **Bin/Location management** — zone, aisle, rack, shelf, bin hierarchy
- **Purchase Order management** — create, track, receive POs
- **Sales Order fulfillment** — pick lists, packing slips, shipping labels
- **Stock transfers** — between warehouses or zones
- **Cycle counting & stocktake** — scheduled and ad-hoc inventory audits
- **Batch/Lot/Expiry tracking** — for perishable or regulated goods
- **Multi-warehouse support** — centralized management
- **Reporting & analytics** — stock aging, turnover, accuracy
- **3rd-party integration** — REST API + webhooks for ERP, POS, e-commerce

---

## 2. Technology Stack (All Free / Open-Source)

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| Backend | FastAPI | MIT | REST API + WebSocket |
| Frontend | Next.js 14+ (PWA) | MIT | Dashboard + mobile scan UI |
| Database | PostgreSQL 16 | PostgreSQL License | Primary storage |
| Cache | Redis / Valkey | BSD | Cache, pub/sub, task queue |
| Task Queue | Celery | BSD | Background jobs (reports, alerts) |
| Barcode Gen | `python-barcode` | MIT | Generate barcodes |
| QR Code | `qrcode` + `Pillow` | BSD/MIT | Generate QR codes |
| Barcode Scan | `html5-qrcode` (JS) | Apache 2.0 | Browser-based barcode/QR scanning |
| PDF | `weasyprint` | BSD | PDF generation (labels, reports) |
| CSV/Excel | `openpyxl` | MIT | Excel import/export |
| UI | shadcn/ui + Tailwind CSS | MIT | Component library |
| Charts | Recharts | MIT | Analytics charts |
| State | Zustand | MIT | Frontend state management |
| Search | PostgreSQL Full-Text Search | — | Product/SKU search (no Elasticsearch needed) |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              WareFlow Frontend (Next.js PWA)                  │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Desktop  │ │ Mobile    │ │ Scan     │ │ Reports      │  │
│  │ Dashboard│ │ Dashboard │ │ Interface│ │ Dashboard    │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Inventory│ │ Inbound  │ │ Outbound │ │ Location      │  │
│  │ Service  │ │ Service  │ │ Service  │ │ Service       │  │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├───────────────┤  │
│  │ Purchase │ │ Transfer │ │ Count    │ │ Report        │  │
│  │ Order Svc│ │ Service  │ │ Service  │ │ Service       │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  Redis (Cache) │ Celery (Tasks) │ PostgreSQL (Data)          │
└──────────────────────────────────────────────────────────────┘
```

### Warehouse Location Hierarchy

```
Warehouse
  └── Zone (e.g., "Receiving", "Storage-A", "Cold Storage", "Shipping")
       └── Aisle (e.g., "A1", "A2")
            └── Rack (e.g., "R1", "R2")
                 └── Shelf (e.g., "S1", "S2", "S3")
                      └── Bin (e.g., "B1", "B2") ← smallest location unit
                           
Location Code Format: WH01-ZONA-A1-R2-S3-B1
```

---

## 4. Database Schema

```sql
-- Warehouses
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL, -- 'WH01', 'WH02'
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    manager_name VARCHAR(200),
    phone VARCHAR(50),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Locations (hierarchical)
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES locations(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL, -- full path code 'WH01-ZONA-A1-R2-S3-B1'
    name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL, -- 'zone', 'aisle', 'rack', 'shelf', 'bin'
    location_type VARCHAR(30), -- 'receiving', 'storage', 'picking', 'packing', 'shipping', 'cold', 'hazmat'
    max_weight_kg DECIMAL(10, 2),
    max_volume_m3 DECIMAL(10, 4),
    is_pickable BOOLEAN DEFAULT true, -- can items be picked from here
    is_active BOOLEAN DEFAULT true,
    barcode VARCHAR(100), -- scannable barcode for this location
    sort_order INT DEFAULT 0,
    UNIQUE(warehouse_id, code)
);

-- Product Categories
CREATE TABLE product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    parent_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    description TEXT,
    sort_order INT DEFAULT 0
);

-- Products (master catalog)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    category_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    barcode VARCHAR(100), -- EAN/UPC barcode
    unit_of_measure VARCHAR(30) NOT NULL, -- 'piece', 'box', 'carton', 'pallet', 'kg', 'liter'
    weight_kg DECIMAL(10, 4),
    length_cm DECIMAL(10, 2),
    width_cm DECIMAL(10, 2),
    height_cm DECIMAL(10, 2),
    cost_price DECIMAL(12, 2),
    sell_price DECIMAL(12, 2),
    min_stock_level DECIMAL(12, 3) DEFAULT 0, -- reorder point
    max_stock_level DECIMAL(12, 3), -- max capacity
    reorder_quantity DECIMAL(12, 3), -- how much to reorder
    is_batch_tracked BOOLEAN DEFAULT false, -- requires lot/batch tracking
    is_serial_tracked BOOLEAN DEFAULT false, -- requires serial number tracking
    is_perishable BOOLEAN DEFAULT false, -- has expiry date
    storage_requirements VARCHAR(100), -- 'ambient', 'cold', 'frozen', 'hazmat'
    image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inventory (stock per product per location)
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID REFERENCES locations(id) ON DELETE CASCADE,
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity_on_hand DECIMAL(12, 3) NOT NULL DEFAULT 0,
    quantity_reserved DECIMAL(12, 3) NOT NULL DEFAULT 0, -- allocated to orders
    quantity_available DECIMAL(12, 3) GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    batch_number VARCHAR(100),
    lot_number VARCHAR(100),
    serial_number VARCHAR(100),
    expiry_date DATE,
    manufacture_date DATE,
    last_counted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, location_id, COALESCE(batch_number, ''), COALESCE(serial_number, ''))
);

-- Suppliers
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(300) NOT NULL,
    code VARCHAR(20) UNIQUE,
    contact_person VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    payment_terms VARCHAR(100), -- 'Net 30', 'COD'
    lead_time_days INT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product ↔ Supplier mapping
CREATE TABLE product_suppliers (
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_sku VARCHAR(100),
    cost_price DECIMAL(12, 2),
    lead_time_days INT,
    min_order_quantity DECIMAL(12, 3),
    is_preferred BOOLEAN DEFAULT false,
    PRIMARY KEY (product_id, supplier_id)
);

-- Purchase Orders
CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(30) UNIQUE NOT NULL, -- auto-generated 'PO-2026-00001'
    supplier_id UUID REFERENCES suppliers(id),
    warehouse_id UUID REFERENCES warehouses(id),
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    -- 'draft', 'submitted', 'confirmed', 'partially_received', 'received', 'cancelled'
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    subtotal DECIMAL(12, 2) DEFAULT 0,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    shipping_cost DECIMAL(12, 2) DEFAULT 0,
    total DECIMAL(12, 2) DEFAULT 0,
    notes TEXT,
    created_by UUID,
    approved_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id UUID REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    quantity_ordered DECIMAL(12, 3) NOT NULL,
    quantity_received DECIMAL(12, 3) DEFAULT 0,
    unit_cost DECIMAL(12, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    notes TEXT
);

-- Goods Receipt (Inbound)
CREATE TABLE goods_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number VARCHAR(30) UNIQUE NOT NULL, -- 'GR-2026-00001'
    purchase_order_id UUID REFERENCES purchase_orders(id),
    warehouse_id UUID REFERENCES warehouses(id),
    supplier_id UUID REFERENCES suppliers(id),
    received_by UUID,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'inspecting', 'put_away', 'completed'
    received_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE goods_receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goods_receipt_id UUID REFERENCES goods_receipts(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    po_item_id UUID REFERENCES purchase_order_items(id),
    quantity_received DECIMAL(12, 3) NOT NULL,
    quantity_accepted DECIMAL(12, 3), -- after inspection
    quantity_rejected DECIMAL(12, 3) DEFAULT 0,
    rejection_reason TEXT,
    put_away_location_id UUID REFERENCES locations(id),
    batch_number VARCHAR(100),
    lot_number VARCHAR(100),
    serial_number VARCHAR(100),
    expiry_date DATE,
    notes TEXT
);

-- Sales Orders (Outbound)
CREATE TABLE sales_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    so_number VARCHAR(30) UNIQUE NOT NULL, -- 'SO-2026-00001'
    customer_name VARCHAR(300),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    shipping_address TEXT,
    warehouse_id UUID REFERENCES warehouses(id),
    status VARCHAR(30) DEFAULT 'pending',
    -- 'pending', 'allocated', 'picking', 'picked', 'packing', 'packed', 'shipped', 'delivered', 'cancelled'
    priority VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    order_date DATE DEFAULT CURRENT_DATE,
    required_date DATE,
    shipped_date DATE,
    subtotal DECIMAL(12, 2) DEFAULT 0,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    shipping_cost DECIMAL(12, 2) DEFAULT 0,
    total DECIMAL(12, 2) DEFAULT 0,
    tracking_number VARCHAR(200),
    shipping_carrier VARCHAR(100),
    notes TEXT,
    external_reference VARCHAR(200), -- reference from 3rd-party system
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sales_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    quantity_ordered DECIMAL(12, 3) NOT NULL,
    quantity_allocated DECIMAL(12, 3) DEFAULT 0,
    quantity_picked DECIMAL(12, 3) DEFAULT 0,
    quantity_shipped DECIMAL(12, 3) DEFAULT 0,
    unit_price DECIMAL(12, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    pick_location_id UUID REFERENCES locations(id), -- suggested pick location
    notes TEXT
);

-- Pick Lists
CREATE TABLE pick_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pick_number VARCHAR(30) UNIQUE NOT NULL,
    warehouse_id UUID REFERENCES warehouses(id),
    assigned_to UUID, -- picker staff
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'cancelled'
    pick_type VARCHAR(20) DEFAULT 'single', -- 'single', 'batch', 'wave'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pick_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pick_list_id UUID REFERENCES pick_lists(id) ON DELETE CASCADE,
    sales_order_item_id UUID REFERENCES sales_order_items(id),
    product_id UUID REFERENCES products(id),
    from_location_id UUID REFERENCES locations(id),
    quantity_to_pick DECIMAL(12, 3) NOT NULL,
    quantity_picked DECIMAL(12, 3) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'picked', 'short', 'skipped'
    picked_at TIMESTAMPTZ,
    notes TEXT
);

-- Stock Transfers (between warehouses or locations)
CREATE TABLE stock_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_number VARCHAR(30) UNIQUE NOT NULL,
    from_warehouse_id UUID REFERENCES warehouses(id),
    to_warehouse_id UUID REFERENCES warehouses(id),
    from_location_id UUID REFERENCES locations(id),
    to_location_id UUID REFERENCES locations(id),
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'in_transit', 'received', 'cancelled'
    reason TEXT,
    initiated_by UUID,
    received_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE stock_transfer_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id UUID REFERENCES stock_transfers(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    quantity DECIMAL(12, 3) NOT NULL,
    batch_number VARCHAR(100),
    serial_number VARCHAR(100)
);

-- Stock Count (Inventory Audit)
CREATE TABLE stock_counts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    count_number VARCHAR(30) UNIQUE NOT NULL,
    warehouse_id UUID REFERENCES warehouses(id),
    count_type VARCHAR(20) NOT NULL, -- 'full', 'cycle', 'spot'
    status VARCHAR(20) DEFAULT 'planned', -- 'planned', 'in_progress', 'completed', 'cancelled'
    location_filter JSONB, -- specific locations to count, NULL = all
    product_filter JSONB, -- specific products, NULL = all
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE stock_count_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_count_id UUID REFERENCES stock_counts(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    location_id UUID REFERENCES locations(id),
    system_quantity DECIMAL(12, 3) NOT NULL, -- expected from system
    counted_quantity DECIMAL(12, 3), -- actual count
    variance DECIMAL(12, 3), -- counted - system
    batch_number VARCHAR(100),
    notes TEXT,
    counted_by UUID,
    counted_at TIMESTAMPTZ
);

-- Inventory Transactions (audit trail)
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    warehouse_id UUID REFERENCES warehouses(id),
    location_id UUID REFERENCES locations(id),
    transaction_type VARCHAR(30) NOT NULL,
    -- 'receive', 'put_away', 'pick', 'ship', 'transfer_out', 'transfer_in',
    -- 'adjustment', 'count', 'waste', 'return'
    quantity_change DECIMAL(12, 3) NOT NULL, -- positive=in, negative=out
    quantity_before DECIMAL(12, 3) NOT NULL,
    quantity_after DECIMAL(12, 3) NOT NULL,
    reference_type VARCHAR(50), -- 'purchase_order', 'sales_order', 'transfer', 'count'
    reference_id UUID,
    batch_number VARCHAR(100),
    serial_number VARCHAR(100),
    notes TEXT,
    performed_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users / Staff
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'admin', 'manager', 'receiver', 'picker', 'packer', 'viewer'
    warehouse_access JSONB DEFAULT '[]', -- warehouse IDs user can access
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. API Endpoints

### Authentication
```
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
```

### Warehouses & Locations
```
GET    /api/v1/warehouses                        - List warehouses
POST   /api/v1/warehouses                       - Create warehouse
GET    /api/v1/warehouses/{id}                   - Warehouse details + stats
PUT    /api/v1/warehouses/{id}                   - Update warehouse
GET    /api/v1/warehouses/{id}/locations          - Location tree
POST   /api/v1/warehouses/{id}/locations          - Create location
PUT    /api/v1/locations/{id}                     - Update location
DELETE /api/v1/locations/{id}                     - Delete location (if empty)
GET    /api/v1/locations/{id}/inventory           - Stock at location
POST   /api/v1/locations/scan/{barcode}           - Lookup location by barcode scan
```

### Products
```
GET    /api/v1/products                           - List products (search, filter, paginate)
POST   /api/v1/products                          - Create product
GET    /api/v1/products/{id}                      - Product detail + stock levels
PUT    /api/v1/products/{id}                      - Update product
DELETE /api/v1/products/{id}                      - Deactivate product
GET    /api/v1/products/{id}/inventory            - Stock across all locations
GET    /api/v1/products/{id}/transactions         - Transaction history
POST   /api/v1/products/scan/{barcode}            - Lookup product by barcode
POST   /api/v1/products/import                    - Bulk import from CSV/Excel
GET    /api/v1/products/export                    - Export product catalog
GET    /api/v1/product-categories                 - List categories
POST   /api/v1/product-categories                - Create category
```

### Inventory
```
GET    /api/v1/inventory                          - Full inventory view (filterable)
GET    /api/v1/inventory/summary                  - Summary by product (total across locations)
GET    /api/v1/inventory/low-stock                - Below minimum stock level
GET    /api/v1/inventory/expiring                 - Items nearing expiry
POST   /api/v1/inventory/adjust                   - Manual stock adjustment
       Body: { product_id, location_id, new_quantity, reason }
GET    /api/v1/inventory/transactions             - All inventory movements
GET    /api/v1/inventory/valuation                - Total inventory valuation
```

### Purchase Orders (Inbound)
```
GET    /api/v1/purchase-orders                    - List POs
POST   /api/v1/purchase-orders                   - Create PO
GET    /api/v1/purchase-orders/{id}               - PO detail
PUT    /api/v1/purchase-orders/{id}               - Update PO (if draft)
POST   /api/v1/purchase-orders/{id}/submit        - Submit PO to supplier
POST   /api/v1/purchase-orders/{id}/cancel        - Cancel PO
POST   /api/v1/purchase-orders/{id}/receive       - Create goods receipt from PO
GET    /api/v1/purchase-orders/{id}/receipts      - Receipts for this PO
```

### Goods Receipt
```
POST   /api/v1/goods-receipts                     - Create receipt (with or without PO)
GET    /api/v1/goods-receipts/{id}                - Receipt detail
PUT    /api/v1/goods-receipts/{id}/inspect        - Quality inspection results
POST   /api/v1/goods-receipts/{id}/put-away       - Assign put-away locations
POST   /api/v1/goods-receipts/{id}/complete       - Complete receiving
```

### Sales Orders (Outbound)
```
GET    /api/v1/sales-orders                       - List sales orders
POST   /api/v1/sales-orders                      - Create sales order
GET    /api/v1/sales-orders/{id}                  - Detail
PUT    /api/v1/sales-orders/{id}                  - Update (if pending)
POST   /api/v1/sales-orders/{id}/allocate         - Allocate stock to order
POST   /api/v1/sales-orders/{id}/pick             - Generate pick list
POST   /api/v1/sales-orders/{id}/pack             - Mark as packed
POST   /api/v1/sales-orders/{id}/ship             - Mark as shipped + tracking
POST   /api/v1/sales-orders/{id}/cancel           - Cancel order
```

### Pick Lists
```
GET    /api/v1/pick-lists                         - List pick lists
GET    /api/v1/pick-lists/{id}                    - Pick list detail
POST   /api/v1/pick-lists/{id}/start              - Start picking
PUT    /api/v1/pick-lists/{id}/items/{iid}        - Update pick item (scan & confirm)
POST   /api/v1/pick-lists/{id}/complete           - Complete pick list
```

### Stock Transfers
```
GET    /api/v1/transfers                          - List transfers
POST   /api/v1/transfers                         - Create transfer
PUT    /api/v1/transfers/{id}                     - Update (if draft)
POST   /api/v1/transfers/{id}/dispatch            - Mark in transit
POST   /api/v1/transfers/{id}/receive             - Receive at destination
```

### Stock Counts
```
GET    /api/v1/stock-counts                       - List counts
POST   /api/v1/stock-counts                      - Create count plan
POST   /api/v1/stock-counts/{id}/start            - Start counting
PUT    /api/v1/stock-counts/{id}/items/{iid}      - Record count
POST   /api/v1/stock-counts/{id}/complete         - Finalize and apply adjustments
GET    /api/v1/stock-counts/{id}/variance         - Variance report
```

### Suppliers
```
GET    /api/v1/suppliers                          - List suppliers
POST   /api/v1/suppliers                         - Create supplier
GET    /api/v1/suppliers/{id}                     - Supplier detail
PUT    /api/v1/suppliers/{id}                     - Update supplier
GET    /api/v1/suppliers/{id}/products            - Products from supplier
GET    /api/v1/suppliers/{id}/purchase-orders     - PO history
```

### Reports
```
GET    /api/v1/reports/stock-summary              - Current stock summary
GET    /api/v1/reports/stock-aging                - Stock aging analysis
GET    /api/v1/reports/stock-turnover             - Turnover rate per product
GET    /api/v1/reports/movement-history           - Inventory movements over period
GET    /api/v1/reports/inbound-summary            - Receiving summary
GET    /api/v1/reports/outbound-summary           - Shipping summary
GET    /api/v1/reports/variance                   - Count variance analysis
GET    /api/v1/reports/valuation                  - Inventory valuation report
GET    /api/v1/reports/expiry-forecast            - Items expiring soon
GET    /api/v1/reports/reorder-suggestions        - Auto reorder suggestions
GET    /api/v1/reports/export                     - Export any report (CSV/PDF/Excel)
```

### Webhooks / 3rd-Party Integration
```
POST   /api/v1/webhooks/config                    - Configure outbound webhooks
POST   /api/v1/integration/incoming-order          - Receive order from external system
       Body: { source: "shopify", external_id: "...", items: [...] }
POST   /api/v1/integration/stock-update            - Push stock update to external system
GET    /api/v1/integration/stock-feed              - Stock feed endpoint (polling)
GET    /api/v1/health                              - Health check
```

---

## 6. Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | KPIs, stock alerts, pending orders, activity feed |
| `/inventory` | Inventory Overview | Stock levels, search, filter |
| `/inventory/{id}` | Product Stock Detail | Stock at all locations, transactions |
| `/products` | Product Catalog | Manage products, categories |
| `/products/{id}` | Product Detail | Edit product, suppliers, stock |
| `/locations` | Location Browser | Warehouse → Zone → Bin tree view |
| `/inbound` | Inbound Dashboard | POs, goods receipts |
| `/inbound/po/new` | Create Purchase Order | New PO form |
| `/inbound/receive` | Receive Goods | Scan & receive with put-away |
| `/outbound` | Outbound Dashboard | Sales orders, shipments |
| `/outbound/so/new` | Create Sales Order | New SO form |
| `/outbound/pick` | Picking Interface | Mobile-friendly pick list (scan) |
| `/outbound/pack` | Packing Interface | Scan & pack items |
| `/transfers` | Stock Transfers | Transfer between warehouses |
| `/counts` | Stock Counts | Cycle count and stocktake |
| `/counts/{id}` | Count Session | Scan & count items |
| `/suppliers` | Suppliers | Supplier management |
| `/reports` | Reports | All analytics and reports |
| `/scan` | Quick Scan | Universal barcode scanner (lookup product/location) |
| `/settings` | Settings | Warehouses, users, integrations |

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Project scaffolding, DB schema, migrations
- [ ] Auth system, user roles
- [ ] Warehouse and location CRUD
- [ ] Product catalog CRUD with categories

### Phase 2: Core Inventory (Week 3-4)
- [ ] Inventory tracking (stock per product per location)
- [ ] Manual stock adjustments
- [ ] Inventory transaction audit trail
- [ ] Barcode generation for products and locations
- [ ] Browser-based barcode scanning (html5-qrcode)

### Phase 3: Inbound (Week 5-6)
- [ ] Supplier management
- [ ] Purchase order creation and management
- [ ] Goods receiving (scan to receive)
- [ ] Put-away process (assign locations)
- [ ] Batch/lot/expiry tracking on receive

### Phase 4: Outbound (Week 7-9)
- [ ] Sales order management
- [ ] Stock allocation engine
- [ ] Pick list generation (optimized route)
- [ ] Mobile-friendly picking interface (scan)
- [ ] Packing and shipping

### Phase 5: Transfers & Counts (Week 10-11)
- [ ] Inter-warehouse/inter-location transfers
- [ ] Cycle count planning
- [ ] Count session (scan & count)
- [ ] Variance report and auto-adjustment

### Phase 6: Reports & Analytics (Week 12-13)
- [ ] Stock summary and aging reports
- [ ] Turnover analysis
- [ ] Reorder suggestions (below min stock)
- [ ] Expiry forecast
- [ ] Export (CSV, PDF, Excel)
- [ ] Dashboard KPIs and charts

### Phase 7: Integration & Polish (Week 14-15)
- [ ] Incoming order webhook (external e-commerce)
- [ ] Stock feed API (real-time stock for external systems)
- [ ] Outbound webhook notifications
- [ ] Print labels (barcode labels for products/locations)
- [ ] Full API documentation
