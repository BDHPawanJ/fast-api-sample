"""Tests for API documentation exposure."""

import importlib

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.core.config import settings

DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


@pytest.fixture
def build_client(monkeypatch):
    """
    Build a client for an app created with the given DOCS_ENABLED value.

    Docs routes are decided when app.main is imported, so the module is
    reloaded with patched settings and reloaded again afterwards.
    """

    def _build(docs_enabled: bool) -> AsyncClient:
        monkeypatch.setattr(settings, "DOCS_ENABLED", docs_enabled)
        app = importlib.reload(main_module).app
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _build
    monkeypatch.undo()
    importlib.reload(main_module)


@pytest.mark.asyncio
class TestDocsExposure:
    """Docs endpoints should exist only when DOCS_ENABLED is set."""

    async def test_docs_disabled(self, build_client):
        """Disabled docs should return 404 and not be advertised."""
        async with build_client(docs_enabled=False) as client:
            for path in DOC_PATHS:
                assert (await client.get(path)).status_code == 404, path

            root = (await client.get("/")).json()
            assert root["docs"] is None
            assert root["redoc"] is None

    async def test_docs_enabled(self, build_client):
        """Enabled docs should be served and advertised."""
        async with build_client(docs_enabled=True) as client:
            for path in DOC_PATHS:
                assert (await client.get(path)).status_code == 200, path

            root = (await client.get("/")).json()
            assert root["docs"] == "/docs"
            assert root["redoc"] == "/redoc"
