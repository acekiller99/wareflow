import pytest
import uuid
from httpx import AsyncClient


async def _setup_po_data(auth_client: AsyncClient):
    """Create warehouse, supplier, product for PO tests."""
    wh = await auth_client.post("/api/v1/warehouses", json={
        "name": "PO Warehouse", "code": "WHPO"
    })
    wh_id = wh.json()["id"]

    sup = await auth_client.post("/api/v1/suppliers", json={
        "name": "PO Supplier", "code": "SUPPO"
    })
    sup_id = sup.json()["id"]

    prod = await auth_client.post("/api/v1/products", json={
        "sku": "PO-PROD-001", "name": "PO Product", "unit_of_measure": "piece"
    })
    prod_id = prod.json()["id"]

    return wh_id, sup_id, prod_id


@pytest.mark.asyncio
class TestPurchaseOrders:
    async def test_create_po(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        response = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "100", "unit_cost": "5.00"}
            ]
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert data["po_number"].startswith("PO-")
        assert len(data["items"]) == 1
        assert float(data["total"]) == 500.0

    async def test_submit_po(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        po = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "50", "unit_cost": "3.00"}
            ]
        })
        po_id = po.json()["id"]
        response = await auth_client.post(f"/api/v1/purchase-orders/{po_id}/submit")
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"

    async def test_cancel_po(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        po = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "10", "unit_cost": "1.00"}
            ]
        })
        po_id = po.json()["id"]
        response = await auth_client.post(f"/api/v1/purchase-orders/{po_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_list_pos(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/purchase-orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_po(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        po = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "20", "unit_cost": "2.00"}
            ]
        })
        po_id = po.json()["id"]
        response = await auth_client.get(f"/api/v1/purchase-orders/{po_id}")
        assert response.status_code == 200
        assert response.json()["id"] == po_id

    async def test_cannot_update_submitted_po(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        po = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "5", "unit_cost": "1.00"}
            ]
        })
        po_id = po.json()["id"]
        await auth_client.post(f"/api/v1/purchase-orders/{po_id}/submit")
        response = await auth_client.put(f"/api/v1/purchase-orders/{po_id}", json={
            "supplier_id": sup_id,
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "999", "unit_cost": "1.00"}
            ]
        })
        assert response.status_code == 409


@pytest.mark.asyncio
class TestGoodsReceipts:
    async def test_create_goods_receipt(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        response = await auth_client.post("/api/v1/goods-receipts", json={
            "warehouse_id": wh_id,
            "supplier_id": sup_id,
            "items": [
                {"product_id": prod_id, "quantity_received": "100"}
            ]
        })
        assert response.status_code == 201
        data = response.json()
        assert data["receipt_number"].startswith("GR-")
        assert data["status"] == "pending"

    async def test_get_goods_receipt(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        gr = await auth_client.post("/api/v1/goods-receipts", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_received": "50"}
            ]
        })
        gr_id = gr.json()["id"]
        response = await auth_client.get(f"/api/v1/goods-receipts/{gr_id}")
        assert response.status_code == 200

    async def test_complete_receipt(self, auth_client: AsyncClient):
        wh_id, sup_id, prod_id = await _setup_po_data(auth_client)
        gr = await auth_client.post("/api/v1/goods-receipts", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_received": "25"}
            ]
        })
        gr_id = gr.json()["id"]
        response = await auth_client.post(f"/api/v1/goods-receipts/{gr_id}/complete")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
