import pytest
import uuid
from httpx import AsyncClient


async def _setup_so_data(auth_client: AsyncClient, suffix: str = ""):
    """Create warehouse, location, product with stock for SO tests."""
    wh = await auth_client.post("/api/v1/warehouses", json={
        "name": f"SO WH{suffix}", "code": f"WHSO{suffix}"
    })
    wh_id = wh.json()["id"]

    loc = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
        "code": f"WHSO{suffix}-BIN1", "name": "Bin 1", "level": "bin"
    })
    loc_id = loc.json()["id"]

    prod = await auth_client.post("/api/v1/products", json={
        "sku": f"SO-PROD{suffix}", "name": f"SO Product{suffix}",
        "unit_of_measure": "piece"
    })
    prod_id = prod.json()["id"]

    # Add inventory
    await auth_client.post("/api/v1/inventory/adjust", json={
        "product_id": prod_id,
        "location_id": loc_id,
        "new_quantity": "500",
        "reason": "Test setup",
    })

    return wh_id, loc_id, prod_id


@pytest.mark.asyncio
class TestSalesOrders:
    async def test_create_sales_order(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_so_data(auth_client, "1")
        response = await auth_client.post("/api/v1/sales-orders", json={
            "warehouse_id": wh_id,
            "customer_name": "Test Customer",
            "items": [
                {"product_id": prod_id, "quantity_ordered": "10", "unit_price": "19.99"}
            ]
        })
        assert response.status_code == 201
        data = response.json()
        assert data["so_number"].startswith("SO-")
        assert data["status"] == "pending"
        assert data["customer_name"] == "Test Customer"

    async def test_allocate_stock(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_so_data(auth_client, "2")
        so = await auth_client.post("/api/v1/sales-orders", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "5", "unit_price": "10.00"}
            ]
        })
        so_id = so.json()["id"]
        response = await auth_client.post(f"/api/v1/sales-orders/{so_id}/allocate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "allocated"
        assert float(data["items"][0]["quantity_allocated"]) == 5.0

    async def test_cancel_order(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_so_data(auth_client, "3")
        so = await auth_client.post("/api/v1/sales-orders", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "5", "unit_price": "10.00"}
            ]
        })
        so_id = so.json()["id"]
        response = await auth_client.post(f"/api/v1/sales-orders/{so_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_list_sales_orders(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/sales-orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_update_pending_order(self, auth_client: AsyncClient):
        wh_id, loc_id, prod_id = await _setup_so_data(auth_client, "4")
        so = await auth_client.post("/api/v1/sales-orders", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "1", "unit_price": "5.00"}
            ]
        })
        so_id = so.json()["id"]
        response = await auth_client.put(f"/api/v1/sales-orders/{so_id}", json={
            "customer_name": "Updated Customer",
            "priority": "high",
        })
        assert response.status_code == 200
        assert response.json()["customer_name"] == "Updated Customer"
        assert response.json()["priority"] == "high"

    async def test_full_outbound_flow(self, auth_client: AsyncClient):
        """Test the full flow: create → allocate → pick → pack → ship."""
        wh_id, loc_id, prod_id = await _setup_so_data(auth_client, "FLOW")

        # Create SO
        so = await auth_client.post("/api/v1/sales-orders", json={
            "warehouse_id": wh_id,
            "items": [
                {"product_id": prod_id, "quantity_ordered": "10", "unit_price": "15.00"}
            ]
        })
        so_id = so.json()["id"]
        assert so.json()["status"] == "pending"

        # Allocate
        alloc = await auth_client.post(f"/api/v1/sales-orders/{so_id}/allocate")
        assert alloc.json()["status"] == "allocated"

        # Generate pick list
        pick = await auth_client.post(f"/api/v1/sales-orders/{so_id}/pick")
        assert pick.status_code == 200
        pl_id = pick.json()["id"]
        assert pick.json()["pick_number"].startswith("PK-")

        # Start picking
        start = await auth_client.post(f"/api/v1/pick-lists/{pl_id}/start")
        assert start.json()["status"] == "in_progress"

        # Update pick items
        pick_items = pick.json()["items"]
        for pi in pick_items:
            await auth_client.put(f"/api/v1/pick-lists/{pl_id}/items/{pi['id']}", json={
                "quantity_picked": str(pi["quantity_to_pick"]),
                "status": "picked",
            })

        # Complete pick
        complete = await auth_client.post(f"/api/v1/pick-lists/{pl_id}/complete")
        assert complete.json()["status"] == "completed"

        # Pack
        pack = await auth_client.post(f"/api/v1/sales-orders/{so_id}/pack")
        assert pack.json()["status"] == "packed"

        # Ship
        ship = await auth_client.post(f"/api/v1/sales-orders/{so_id}/ship", json={
            "tracking_number": "TRACK-123",
            "shipping_carrier": "FedEx",
        })
        assert ship.json()["status"] == "shipped"
        assert ship.json()["tracking_number"] == "TRACK-123"


@pytest.mark.asyncio
class TestPickLists:
    async def test_list_pick_lists(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/pick-lists")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_nonexistent_pick_list(self, auth_client: AsyncClient):
        response = await auth_client.get(f"/api/v1/pick-lists/{uuid.uuid4()}")
        assert response.status_code == 404
