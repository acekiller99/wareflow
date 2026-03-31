import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWarehouses:
    async def test_create_warehouse(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/warehouses", json={
            "name": "Main Warehouse",
            "code": "WH01",
            "address": "123 Industrial Rd",
            "city": "Austin",
            "country": "USA",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Main Warehouse"
        assert data["code"] == "WH01"
        assert data["is_active"] is True

    async def test_create_duplicate_code(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/warehouses", json={
            "name": "WH-A", "code": "WHDUP"
        })
        response = await auth_client.post("/api/v1/warehouses", json={
            "name": "WH-B", "code": "WHDUP"
        })
        assert response.status_code == 409

    async def test_list_warehouses(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/warehouses", json={
            "name": "List WH", "code": "WHLST"
        })
        response = await auth_client.get("/api/v1/warehouses")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_warehouse(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/warehouses", json={
            "name": "Get WH", "code": "WHGET"
        })
        wh_id = create_resp.json()["id"]
        response = await auth_client.get(f"/api/v1/warehouses/{wh_id}")
        assert response.status_code == 200
        assert response.json()["code"] == "WHGET"

    async def test_get_nonexistent_warehouse(self, auth_client: AsyncClient):
        import uuid
        response = await auth_client.get(f"/api/v1/warehouses/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_update_warehouse(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/warehouses", json={
            "name": "Old Name", "code": "WHUPD"
        })
        wh_id = create_resp.json()["id"]
        response = await auth_client.put(f"/api/v1/warehouses/{wh_id}", json={
            "name": "New Name",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/warehouses")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLocations:
    async def _create_warehouse(self, auth_client: AsyncClient, code: str) -> str:
        resp = await auth_client.post("/api/v1/warehouses", json={
            "name": f"WH {code}", "code": code
        })
        return resp.json()["id"]

    async def test_create_location(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC1")
        response = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "WHLOC1-ZONA",
            "name": "Zone A",
            "level": "zone",
            "location_type": "storage",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "WHLOC1-ZONA"
        assert data["level"] == "zone"

    async def test_create_location_invalid_level(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC2")
        response = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "BAD-LEVEL",
            "name": "Bad",
            "level": "floor",  # invalid
        })
        assert response.status_code == 422

    async def test_list_locations(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC3")
        await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "WHLOC3-Z1", "name": "Zone 1", "level": "zone"
        })
        response = await auth_client.get(f"/api/v1/warehouses/{wh_id}/locations")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_update_location(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC4")
        loc_resp = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "WHLOC4-Z1", "name": "Zone 1", "level": "zone"
        })
        loc_id = loc_resp.json()["id"]
        response = await auth_client.put(f"/api/v1/locations/{loc_id}", json={
            "name": "Updated Zone",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Zone"

    async def test_delete_location(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC5")
        loc_resp = await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "WHLOC5-DEL", "name": "To Delete", "level": "bin"
        })
        loc_id = loc_resp.json()["id"]
        response = await auth_client.delete(f"/api/v1/locations/{loc_id}")
        assert response.status_code == 204

    async def test_scan_location(self, auth_client: AsyncClient):
        wh_id = await self._create_warehouse(auth_client, "WHLOC6")
        await auth_client.post(f"/api/v1/warehouses/{wh_id}/locations", json={
            "code": "WHLOC6-BIN", "name": "Bin", "level": "bin",
            "barcode": "LOC-SCAN-001"
        })
        response = await auth_client.post("/api/v1/locations/scan/LOC-SCAN-001")
        assert response.status_code == 200
        assert response.json()["barcode"] == "LOC-SCAN-001"
