import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestReports:
    async def test_stock_summary(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/stock-summary")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_low_stock_report(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/low-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_reorder_suggestions(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/reorder-suggestions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_expiry_forecast(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/expiry-forecast")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_movement_history(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/movement-history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
