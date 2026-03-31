import pytest
import uuid
from httpx import AsyncClient


async def _setup_transfer_data(auth_client: AsyncClient, suffix: str = ""):
    """Create 2 warehouses, locations, product with stock for transfer tests."""
    wh1 = await auth_client.post("/api/v1/warehouses", json={
        "name": f"From WH{suffix}", "code": f"WHFR{suffix}"
    })
    wh1_id = wh1.json()["id"]

    wh2 = await auth_client.post("/api/v1/warehouses", json={
        "name": f"To WH{suffix}", "code": f"WHTO{suffix}"
    })
    wh2_id = wh2.json()["id"]

    loc1 = await auth_client.post(f"/api/v1/warehouses/{wh1_id}/locations", json={
        "code": f"WHFR{suffix}-B1", "name": "Bin 1", "level": "bin"
    })
    loc1_id = loc1.json()["id"]

    loc2 = await auth_client.post(f"/api/v1/warehouses/{wh2_id}/locations", json={
        "code": f"WHTO{suffix}-B1", "name": "Bin 1", "level": "bin"
    })
    loc2_id = loc2.json()["id"]

    prod = await auth_client.post("/api/v1/products", json={
        "sku": f"TR-PROD{suffix}", "name": f"Transfer Product{suffix}",
        "unit_of_measure": "piece"
    })
    prod_id = prod.json()["id"]

    # Add stock at source
    await auth_client.post("/api/v1/inventory/adjust", json={
        "product_id": prod_id,
        "location_id": loc1_id,
        "new_quantity": "200",
        "reason": "Transfer test setup",
    })

    return wh1_id, wh2_id, loc1_id, loc2_id, prod_id


@pytest.mark.asyncio
class TestStockTransfers:
    async def test_create_transfer(self, auth_client: AsyncClient):
        wh1_id, wh2_id, loc1_id, loc2_id, prod_id = await _setup_transfer_data(auth_client, "1")
        response = await auth_client.post("/api/v1/transfers", json={
            "from_warehouse_id": wh1_id,
            "to_warehouse_id": wh2_id,
            "from_location_id": loc1_id,
            "to_location_id": loc2_id,
            "reason": "Rebalance stock",
            "items": [
                {"product_id": prod_id, "quantity": "50"}
            ]
        })
        assert response.status_code == 201
        data = response.json()
        assert data["transfer_number"].startswith("TR-")
        assert data["status"] == "draft"

    async def test_full_transfer_flow(self, auth_client: AsyncClient):
        """Test: create → dispatch → receive."""
        wh1_id, wh2_id, loc1_id, loc2_id, prod_id = await _setup_transfer_data(auth_client, "FLW")

        # Create
        tr = await auth_client.post("/api/v1/transfers", json={
            "from_warehouse_id": wh1_id,
            "to_warehouse_id": wh2_id,
            "from_location_id": loc1_id,
            "to_location_id": loc2_id,
            "items": [
                {"product_id": prod_id, "quantity": "30"}
            ]
        })
        tr_id = tr.json()["id"]

        # Dispatch
        dispatch = await auth_client.post(f"/api/v1/transfers/{tr_id}/dispatch")
        assert dispatch.json()["status"] == "in_transit"

        # Receive
        receive = await auth_client.post(f"/api/v1/transfers/{tr_id}/receive")
        assert receive.json()["status"] == "received"

    async def test_dispatch_insufficient_stock(self, auth_client: AsyncClient):
        wh1_id, wh2_id, loc1_id, loc2_id, prod_id = await _setup_transfer_data(auth_client, "ISF")
        tr = await auth_client.post("/api/v1/transfers", json={
            "from_warehouse_id": wh1_id,
            "to_warehouse_id": wh2_id,
            "from_location_id": loc1_id,
            "to_location_id": loc2_id,
            "items": [
                {"product_id": prod_id, "quantity": "9999"}
            ]
        })
        tr_id = tr.json()["id"]
        response = await auth_client.post(f"/api/v1/transfers/{tr_id}/dispatch")
        assert response.status_code == 409

    async def test_list_transfers(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/transfers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
