# WareFlow Implementation Checklist

Use this checklist to verify all features from `03_WAREFLOW_WAREHOUSE_MIS.md` have been implemented correctly.

---

## Phase 1: Foundation

### Project Scaffolding
- [x] Backend (FastAPI) project structure created
- [x] Frontend (Next.js) project structure created
- [x] Docker Compose setup (PostgreSQL, Redis, Backend, Frontend)
- [x] Environment configuration (.env.example)
- [x] Database connection (SQLAlchemy async)
- [x] Alembic migration setup

### Database Schema
- [x] `warehouses` table/model
- [x] `locations` table/model (hierarchical: zone/aisle/rack/shelf/bin)
- [x] `product_categories` table/model
- [x] `products` table/model
- [x] `inventory` table/model (with computed `quantity_available`)
- [x] `suppliers` table/model
- [x] `product_suppliers` table/model
- [x] `purchase_orders` table/model
- [x] `purchase_order_items` table/model
- [x] `goods_receipts` table/model
- [x] `goods_receipt_items` table/model
- [x] `sales_orders` table/model
- [x] `sales_order_items` table/model
- [x] `pick_lists` table/model
- [x] `pick_list_items` table/model
- [x] `stock_transfers` table/model
- [x] `stock_transfer_items` table/model
- [x] `stock_counts` table/model
- [x] `stock_count_items` table/model
- [x] `inventory_transactions` table/model (audit trail)
- [x] `users` table/model

### Auth System
- [x] `POST /api/v1/auth/login` — JWT login
- [x] `POST /api/v1/auth/register` — User registration
- [x] `GET /api/v1/auth/me` — Current user info
- [x] Password hashing (bcrypt)
- [x] JWT token creation & validation
- [x] Role-based access control helper (`require_role`)

---

## Phase 2: Core Inventory

### Warehouse & Location CRUD
- [x] `GET /api/v1/warehouses` — List warehouses
- [x] `POST /api/v1/warehouses` — Create warehouse (unique code)
- [x] `GET /api/v1/warehouses/{id}` — Warehouse details
- [x] `PUT /api/v1/warehouses/{id}` — Update warehouse
- [x] `GET /api/v1/warehouses/{id}/locations` — Location tree
- [x] `POST /api/v1/warehouses/{id}/locations` — Create location
- [x] `PUT /api/v1/locations/{id}` — Update location
- [x] `DELETE /api/v1/locations/{id}` — Delete location (only if empty)
- [x] `GET /api/v1/locations/{id}/inventory` — Stock at location
- [x] `POST /api/v1/locations/scan/{barcode}` — Lookup location by barcode

### Product Catalog CRUD
- [x] `GET /api/v1/products` — List products (search, filter, paginate)
- [x] `POST /api/v1/products` — Create product (unique SKU)
- [x] `GET /api/v1/products/{id}` — Product detail
- [x] `PUT /api/v1/products/{id}` — Update product
- [x] `DELETE /api/v1/products/{id}` — Deactivate product (soft delete)
- [x] `GET /api/v1/products/{id}/inventory` — Stock across all locations
- [x] `GET /api/v1/products/{id}/transactions` — Transaction history
- [x] `POST /api/v1/products/scan/{barcode}` — Lookup product by barcode
- [x] `GET /api/v1/product-categories` — List categories
- [x] `POST /api/v1/product-categories` — Create category

### Inventory Management
- [x] `GET /api/v1/inventory` — Full inventory view (filterable)
- [x] `GET /api/v1/inventory/low-stock` — Below minimum stock level
- [x] `GET /api/v1/inventory/expiring` — Items nearing expiry
- [x] `POST /api/v1/inventory/adjust` — Manual stock adjustment (with audit trail)
- [x] `GET /api/v1/inventory/transactions` — All inventory movements

---

## Phase 3: Inbound

### Supplier Management
- [x] `GET /api/v1/suppliers` — List suppliers
- [x] `POST /api/v1/suppliers` — Create supplier
- [x] `GET /api/v1/suppliers/{id}` — Supplier detail
- [x] `PUT /api/v1/suppliers/{id}` — Update supplier
- [x] `GET /api/v1/suppliers/{id}/products` — Products from supplier
- [x] `GET /api/v1/suppliers/{id}/purchase-orders` — PO history

### Purchase Orders
- [x] `GET /api/v1/purchase-orders` — List POs
- [x] `POST /api/v1/purchase-orders` — Create PO (auto-numbering)
- [x] `GET /api/v1/purchase-orders/{id}` — PO detail
- [x] `PUT /api/v1/purchase-orders/{id}` — Update PO (draft only)
- [x] `POST /api/v1/purchase-orders/{id}/submit` — Submit PO
- [x] `POST /api/v1/purchase-orders/{id}/cancel` — Cancel PO
- [x] `POST /api/v1/purchase-orders/{id}/receive` — Create goods receipt from PO
- [x] `GET /api/v1/purchase-orders/{id}/receipts` — Receipts for PO

### Goods Receipts
- [x] `POST /api/v1/goods-receipts` — Create receipt (with or without PO)
- [x] `GET /api/v1/goods-receipts/{id}` — Receipt detail
- [x] `PUT /api/v1/goods-receipts/{id}/inspect` — Quality inspection results
- [x] `POST /api/v1/goods-receipts/{id}/put-away` — Assign put-away locations (updates inventory)
- [x] `POST /api/v1/goods-receipts/{id}/complete` — Complete receiving

---

## Phase 4: Outbound

### Sales Orders
- [x] `GET /api/v1/sales-orders` — List sales orders
- [x] `POST /api/v1/sales-orders` — Create sales order (auto-numbering)
- [x] `GET /api/v1/sales-orders/{id}` — Detail
- [x] `PUT /api/v1/sales-orders/{id}` — Update (pending only)
- [x] `POST /api/v1/sales-orders/{id}/allocate` — Allocate stock (FEFO)
- [x] `POST /api/v1/sales-orders/{id}/pick` — Generate pick list
- [x] `POST /api/v1/sales-orders/{id}/pack` — Mark as packed
- [x] `POST /api/v1/sales-orders/{id}/ship` — Mark as shipped (deducts inventory)
- [x] `POST /api/v1/sales-orders/{id}/cancel` — Cancel order (releases reserved)

### Pick Lists
- [x] `GET /api/v1/pick-lists` — List pick lists
- [x] `GET /api/v1/pick-lists/{id}` — Pick list detail
- [x] `POST /api/v1/pick-lists/{id}/start` — Start picking
- [x] `PUT /api/v1/pick-lists/{id}/items/{iid}` — Update pick item
- [x] `POST /api/v1/pick-lists/{id}/complete` — Complete pick list

---

## Phase 5: Transfers & Counts

### Stock Transfers
- [x] `GET /api/v1/transfers` — List transfers
- [x] `POST /api/v1/transfers` — Create transfer (auto-numbering)
- [x] `PUT /api/v1/transfers/{id}` — Update (draft only)
- [x] `POST /api/v1/transfers/{id}/dispatch` — Deduct from source, mark in transit
- [x] `POST /api/v1/transfers/{id}/receive` — Add to destination, mark received

### Stock Counts
- [x] `GET /api/v1/stock-counts` — List counts
- [x] `POST /api/v1/stock-counts` — Create count plan (populates items from inventory)
- [x] `POST /api/v1/stock-counts/{id}/start` — Start counting
- [x] `PUT /api/v1/stock-counts/{id}/items/{iid}` — Record count
- [x] `POST /api/v1/stock-counts/{id}/complete` — Finalize and apply adjustments
- [x] `GET /api/v1/stock-counts/{id}/variance` — Variance report

---

## Phase 6: Reports & Analytics

- [x] `GET /api/v1/reports/stock-summary` — Current stock summary
- [x] `GET /api/v1/reports/low-stock` — Low stock report
- [x] `GET /api/v1/reports/reorder-suggestions` — Auto reorder suggestions
- [x] `GET /api/v1/reports/expiry-forecast` — Items expiring soon
- [x] `GET /api/v1/reports/movement-history` — Inventory movements

### Reports (Remaining — Not Yet Implemented)
- [ ] `GET /api/v1/reports/stock-aging` — Stock aging analysis
- [ ] `GET /api/v1/reports/stock-turnover` — Turnover rate per product
- [ ] `GET /api/v1/reports/inbound-summary` — Receiving summary
- [ ] `GET /api/v1/reports/outbound-summary` — Shipping summary
- [ ] `GET /api/v1/reports/variance` — Count variance analysis
- [ ] `GET /api/v1/reports/valuation` — Inventory valuation report
- [ ] `GET /api/v1/reports/export` — Export report (CSV/PDF/Excel)

---

## Phase 7: Integration & Polish

### Integration (Not Yet Implemented)
- [ ] `POST /api/v1/webhooks/config` — Configure outbound webhooks
- [ ] `POST /api/v1/integration/incoming-order` — Receive order from external system
- [ ] `POST /api/v1/integration/stock-update` — Push stock update to external system
- [ ] `GET /api/v1/integration/stock-feed` — Stock feed endpoint (polling)

### Other (Not Yet Implemented)
- [ ] `POST /api/v1/products/import` — Bulk import from CSV/Excel
- [ ] `GET /api/v1/products/export` — Export product catalog
- [ ] `GET /api/v1/inventory/summary` — Summary by product
- [ ] `GET /api/v1/inventory/valuation` — Inventory valuation
- [ ] Print labels (barcode labels for products/locations)
- [ ] WebSocket real-time updates

---

## Infrastructure

- [x] Health check endpoint (`GET /api/v1/health`)
- [x] CORS configuration
- [x] Docker Compose (PostgreSQL, Redis, Backend, Frontend)
- [x] Backend Dockerfile
- [x] Frontend Dockerfile
- [x] Environment variable configuration

---

## Automated Tests

### Test Coverage
- [x] `test_auth.py` — Registration, login, JWT validation, password rules (8 tests)
- [x] `test_warehouses.py` — Warehouse CRUD, location CRUD, barcode scan (13 tests)
- [x] `test_products.py` — Product CRUD, categories, search, barcode scan (11 tests)
- [x] `test_suppliers.py` — Supplier CRUD, duplicate code prevention (6 tests)
- [x] `test_inventory.py` — Stock adjustment, audit trail, validation (4 tests)
- [x] `test_inbound.py` — Purchase orders, goods receipts, status flow (9 tests)
- [x] `test_outbound.py` — Sales orders, full outbound flow, pick lists (8 tests)
- [x] `test_transfers.py` — Stock transfers, full flow, insufficient stock (4 tests)
- [x] `test_stock_counts.py` — Stock counts, full flow, variance (4 tests)
- [x] `test_reports.py` — All report endpoints, health check (6 tests)

### Running Tests
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Frontend Pages (Scaffolding Only)

- [x] `/` — Dashboard landing page
- [x] API client utility (`src/lib/api.ts`)
- [ ] `/inventory` — Inventory overview
- [ ] `/products` — Product catalog
- [ ] `/locations` — Location browser
- [ ] `/inbound` — Inbound dashboard
- [ ] `/outbound` — Outbound dashboard
- [ ] `/transfers` — Stock transfers
- [ ] `/counts` — Stock counts
- [ ] `/suppliers` — Suppliers
- [ ] `/reports` — Reports
- [ ] `/scan` — Quick scan
- [ ] `/settings` — Settings
