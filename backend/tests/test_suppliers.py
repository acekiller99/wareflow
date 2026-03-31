import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSuppliers:
    async def test_create_supplier(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/suppliers", json={
            "name": "Acme Corp",
            "code": "SUP01",
            "contact_person": "John Doe",
            "email": "john@acme.com",
            "payment_terms": "Net 30",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corp"
        assert data["code"] == "SUP01"

    async def test_create_duplicate_code(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/suppliers", json={
            "name": "S1", "code": "DUPCODE"
        })
        response = await auth_client.post("/api/v1/suppliers", json={
            "name": "S2", "code": "DUPCODE"
        })
        assert response.status_code == 409

    async def test_list_suppliers(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/suppliers", json={
            "name": "List Supplier", "code": "SUPLST"
        })
        response = await auth_client.get("/api/v1/suppliers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_supplier(self, auth_client: AsyncClient):
        create = await auth_client.post("/api/v1/suppliers", json={
            "name": "Get Supplier", "code": "SUPGET"
        })
        sid = create.json()["id"]
        response = await auth_client.get(f"/api/v1/suppliers/{sid}")
        assert response.status_code == 200
        assert response.json()["code"] == "SUPGET"

    async def test_update_supplier(self, auth_client: AsyncClient):
        create = await auth_client.post("/api/v1/suppliers", json={
            "name": "Old Supplier", "code": "SUPUPD"
        })
        sid = create.json()["id"]
        response = await auth_client.put(f"/api/v1/suppliers/{sid}", json={
            "name": "Updated Supplier",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Supplier"

    async def test_get_nonexistent(self, auth_client: AsyncClient):
        response = await auth_client.get(f"/api/v1/suppliers/{uuid.uuid4()}")
        assert response.status_code == 404
