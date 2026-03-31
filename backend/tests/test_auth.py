import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuth:
    async def test_register_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "securepass123",
            "full_name": "New User",
            "role": "viewer",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "viewer"
        assert "id" in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": "admin@wareflow.test",
            "password": "password123",
            "full_name": "Duplicate",
            "role": "viewer",
        })
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "admin@wareflow.test",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "admin@wareflow.test",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert response.status_code == 401

    async def test_get_me_authenticated(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@wareflow.test"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_password_min_length(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "12345",
            "full_name": "Short Pass",
            "role": "viewer",
        })
        assert response.status_code == 422
