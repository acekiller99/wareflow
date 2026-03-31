import pytest
from httpx import AsyncClient


async def _setup_warehouse_location_product(auth_client: AsyncClient):
    """Helper: create a warehouse, location, and product for inventory tests."""
    wh = await auth_client.post("/api/v1/warehouses", json={
        "name": "Inv Warehouse", "code": "WHINV"
    })
    wh_id = wh.json()["id"]

    loc = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
        "code": "WHINV-BIN1", "name": "Bin 1", "level": "bin"
    })
    loc_id = loc.json()["id"]

    prod = await auth_client.post("/api/v1/products", json={
        "sku": "INV-PROD-001", "name": "Inventory Product",
        "unit_of_measure": "piece", "min_stock_level": "100"
    })
    prod_id = prod.json()["id"]

    return wh_id, loc_id, prod_id


@pytest.mark.asyncio
class TestInventory:
    async def test_adjust_stock(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_warehouse_location_product(auth_client)

        response = await auth_client.post("/api/v1/inventory/adjust", json={
            "product_id": prod_id,
            "location_id": loc_id,
            "new_quantity": "50",
            "reason": "Initial stock",
        })
        assert response.status_code == 200
        data = response.json()
        assert float(data["quantity_on_hand"]) == 50.0

    async def test_adjust_creates_transaction(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_warehouse_location_product(auth_client)
        await auth_client.post("/api/v1/inventory/adjust", json={
            "product_id": prod_id,
            "location_id": loc_id,
            "new_quantity": "75",
            "reason": "Test adjust",
        })

        response = await auth_client.get("/api/v1/inventory/transactions")
        assert response.status_code == 200
        txns = response.json()
        assert len(txns) >= 1
        assert any(t["transaction_type"] == "adjustment" for t in txns)

    async def test_list_inventory(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/inventory")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_adjust_requires_reason(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/inventory/adjust", json={
            "product_id": "00000000-0000-0000-0000-000000000001",
            "location_id": "00000000-0000-0000-0000-000000000002",
            "new_quantity": "10",
            "reason": "",
        })
        assert response.status_code == 422
