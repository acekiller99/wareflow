import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestProductCategories:
    async def test_create_category(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/product-categories", json={
            "name": "Electronics",
            "description": "Electronic goods",
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Electronics"

    async def test_list_categories(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/product-categories", json={"name": "Cat-List"})
        response = await auth_client.get("/api/v1/product-categories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
class TestProducts:
    async def test_create_product(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/products", json={
            "sku": "PROD-001",
            "name": "Widget A",
            "unit_of_measure": "piece",
            "cost_price": "10.50",
            "sell_price": "19.99",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "PROD-001"
        assert data["name"] == "Widget A"
        assert data["is_active"] is True

    async def test_create_duplicate_sku(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/products", json={
            "sku": "DUP-SKU", "name": "First", "unit_of_measure": "piece"
        })
        response = await auth_client.post("/api/v1/products", json={
            "sku": "DUP-SKU", "name": "Second", "unit_of_measure": "piece"
        })
        assert response.status_code == 409

    async def test_list_products(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/products", json={
            "sku": "LIST-001", "name": "List Product", "unit_of_measure": "box"
        })
        response = await auth_client.get("/api/v1/products")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_search_products(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/products", json={
            "sku": "SEARCH-001", "name": "Searchable Widget", "unit_of_measure": "piece"
        })
        response = await auth_client.get("/api/v1/products?search=Searchable")
        assert response.status_code == 200
        results = response.json()
        assert any(p["name"] == "Searchable Widget" for p in results)

    async def test_get_product(self, auth_client: AsyncClient):
        create = await auth_client.post("/api/v1/products", json={
            "sku": "GET-001", "name": "Get Product", "unit_of_measure": "piece"
        })
        pid = create.json()["id"]
        response = await auth_client.get(f"/api/v1/products/{pid}")
        assert response.status_code == 200
        assert response.json()["sku"] == "GET-001"

    async def test_update_product(self, auth_client: AsyncClient):
        create = await auth_client.post("/api/v1/products", json={
            "sku": "UPD-001", "name": "Original", "unit_of_measure": "piece"
        })
        pid = create.json()["id"]
        response = await auth_client.put(f"/api/v1/products/{pid}", json={
            "name": "Updated Name",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_deactivate_product(self, auth_client: AsyncClient):
        create = await auth_client.post("/api/v1/products", json={
            "sku": "DEL-001", "name": "To Deactivate", "unit_of_measure": "piece"
        })
        pid = create.json()["id"]
        response = await auth_client.delete(f"/api/v1/products/{pid}")
        assert response.status_code == 204
        # Verify it's deactivated, not deleted
        get_resp = await auth_client.get(f"/api/v1/products/{pid}")
        assert get_resp.json()["is_active"] is False

    async def test_scan_product(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/products", json={
            "sku": "SCAN-001", "name": "Scannable", "unit_of_measure": "piece",
            "barcode": "4901234567890"
        })
        response = await auth_client.post("/api/v1/products/scan/4901234567890")
        assert response.status_code == 200
        assert response.json()["barcode"] == "4901234567890"

    async def test_scan_not_found(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/products/scan/NONEXISTENT")
        assert response.status_code == 404
