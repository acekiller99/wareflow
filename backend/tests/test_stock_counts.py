import pytest
import uuid
from httpx import AsyncClient


async def _setup_count_data(auth_client: AsyncClient, suffix: str = ""):
    """Create warehouse, location, product with stock for count tests."""
    wh = await auth_client.post("/api/v1/warehouses", json={
        "name": f"Count WH{suffix}", "code": f"WHCNT{suffix}"
    })
    wh_id = wh.json()["id"]

    loc = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
        "code": f"WHCNT{suffix}-B1", "name": "Bin 1", "level": "bin"
    })
    loc_id = loc.json()["id"]

    prod = await auth_client.post("/api/v1/products", json={
        "sku": f"CNT-PROD{suffix}", "name": f"Count Product{suffix}",
        "unit_of_measure": "piece"
    })
    prod_id = prod.json()["id"]

    await auth_client.post("/api/v1/inventory/adjust", json={
        "product_id": prod_id,
        "location_id": loc_id,
        "new_quantity": "100",
        "reason": "Count test setup",
    })

    return wh_id, loc_id, prod_id


@pytest.mark.asyncio
class TestStockCounts:
    async def test_create_stock_count(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_count_data(auth_client, "1")
        response = await auth_client.post("/api/v1/stock-counts", json={
            "warehouse_id": wh_id,
            "count_type": "cycle",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["count_number"].startswith("SC-")
        assert data["status"] == "planned"
        assert len(data["items"]) >= 1

    async def test_full_count_flow(self, auth_client: AsyncClient):
        """Test: create → start → record → complete."""
        wh_id, loc_id, prod_id = await _setup_count_data(auth_client, "FLW")

        # Create
        sc = await auth_client.post("/api/v1/stock-counts", json={
            "warehouse_id": wh_id,
            "count_type": "spot",
        })
        sc_id = sc.json()["id"]
        items = sc.json()["items"]
        assert len(items) >= 1

        # Start
        start = await auth_client.post(f"/api/v1/stock-counts/{sc_id}/start")
        assert start.json()["status"] == "in_progress"

        # Record counts (actual = 95, variance = -5)
        for item in items:
            await auth_client.put(f"/api/v1/stock-counts/{sc_id}/items/{item['id']}", json={
                "counted_quantity": "95",
                "notes": "Found 5 missing",
            })

        # Check variance
        variance = await auth_client.get(f"/api/v1/stock-counts/{sc_id}/variance")
        assert variance.status_code == 200
        var_items = variance.json()
        assert len(var_items) >= 1
        assert float(var_items[0]["variance"]) == -5.0

        # Complete (applies adjustments)
        complete = await auth_client.post(f"/api/v1/stock-counts/{sc_id}/complete")
        assert complete.json()["status"] == "completed"

    async def test_invalid_count_type(self, auth_client: AsyncClient):
        wh_id, _, _ = await _setup_count_data(auth_client, "INV")
        response = await auth_client.post("/api/v1/stock-counts", json={
            "warehouse_id": wh_id,
            "count_type": "invalid",
        })
        assert response.status_code == 422

    async def test_list_stock_counts(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/stock-counts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
