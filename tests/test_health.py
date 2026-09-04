"""Tests for health endpoints."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app


class _ExecuteResult:
    """Simple async execute result with scalar method."""

    def scalar(self):
        return 1


@pytest.fixture
async def health_client():
    """Create client with mocked DB dependency."""
    fake_db = SimpleNamespace(execute=AsyncMock(return_value=_ExecuteResult()))

    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client, fake_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health API endpoints."""

    async def test_health_check_success(self, health_client):
        """Basic health endpoint should return success payload."""
        client, _ = health_client
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Application is healthy"
        assert data["data"]["status"] == "healthy"

    async def test_database_health_check_success(self, health_client):
        """DB health endpoint should return success payload when DB is reachable."""
        client, _ = health_client
        response = await client.get("/api/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Database is healthy"
        assert data["data"]["database"] == "connected"

    async def test_database_health_check_failure(self, health_client):
        """DB health endpoint should return 503 on DB error."""
        client, fake_db = health_client
        fake_db.execute = AsyncMock(side_effect=Exception("DB is down"))

        response = await client.get("/api/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Service temporarily unavailable"

    async def test_detailed_health_check_degraded_on_db_error(self, health_client):
        """Detailed health endpoint should mark system degraded if DB check fails."""
        client, fake_db = health_client
        fake_db.execute = AsyncMock(side_effect=Exception("DB timeout"))

        response = await client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "System status: degraded"
        assert data["data"]["database"]["status"] == "unhealthy"
