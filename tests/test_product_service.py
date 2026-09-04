"""Unit tests for product service layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import (
    create_product,
    delete_product,
    get_all_products,
    get_low_stock_products,
    get_out_of_stock_products,
    get_product_by_id,
    search_products,
    update_product,
)


class _CountResult:
    """Simple SQLAlchemy-like count result."""

    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _SingleResult:
    """Simple SQLAlchemy-like single-object result."""

    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ListResult:
    """Simple SQLAlchemy-like list result."""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


def _mock_db():
    return SimpleNamespace(
        execute=AsyncMock(),
        add=MagicMock(),
        delete=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
        rollback=AsyncMock(),
    )


@pytest.mark.asyncio
class TestProductService:
    """Product service behavior tests."""

    async def test_create_get_update_delete_product(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Should execute core CRUD operations successfully."""
        db = _mock_db()

        async def set_id(product):
            product.id = 101

        db.refresh.side_effect = set_id
        created = await create_product(
            db,
            ProductCreate(
                name="Laptop",
                description="gaming laptop",
                price=1000.0,
                stock=10,
            ),
        )

        db.execute.return_value = _SingleResult(created)
        fetched = await get_product_by_id(db, created.id)
        assert fetched is created

        monkeypatch.setattr(
            "app.services.product_service.get_product_by_id",
            AsyncMock(return_value=created),
        )
        updated = await update_product(
            db,
            created.id,
            ProductUpdate(name="Laptop Pro", price=1200.0),
        )
        assert updated is created
        assert created.name == "Laptop Pro"
        assert created.price == 1200.0

        deleted = await delete_product(db, created.id)
        assert deleted is True
        db.delete.assert_awaited_once_with(created)

    async def test_update_and_delete_non_existent_product(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Should return None/False for missing products."""
        db = _mock_db()
        monkeypatch.setattr(
            "app.services.product_service.get_product_by_id",
            AsyncMock(return_value=None),
        )

        assert await update_product(db, 999999, ProductUpdate(name="Missing")) is None
        assert await delete_product(db, 999999) is False

    async def test_get_all_products_and_search(self):
        """Should list and search products with pagination."""
        db = _mock_db()
        products = [
            Product(name="MacBook", description="Apple laptop", price=2000.0, stock=5),
            Product(
                name="ThinkPad", description="Business laptop", price=1500.0, stock=12
            ),
        ]
        db.execute.side_effect = [
            _CountResult(3),
            _ListResult(products),
            _CountResult(2),
            _ListResult(products),
        ]

        listed, total_listed = await get_all_products(db, skip=0, limit=2)
        matched, total_matched = await search_products(db, "laptop", skip=0, limit=10)

        assert total_listed == 3
        assert len(listed) == 2
        assert total_matched == 2
        assert len(matched) == 2
        assert all(
            "laptop" in p.name.lower() or "laptop" in (p.description or "").lower()
            for p in matched
        )

    async def test_low_stock_and_out_of_stock_queries(self):
        """Should return correct low and out-of-stock product sets."""
        db = _mock_db()
        low_stock_products = [
            Product(name="LowOne", description="desc", price=10.0, stock=1),
            Product(name="LowFive", description="desc", price=20.0, stock=5),
        ]
        out_of_stock_products = [
            Product(name="Out", description="desc", price=30.0, stock=0),
        ]
        db.execute.side_effect = [
            _CountResult(2),
            _ListResult(low_stock_products),
            _CountResult(1),
            _ListResult(out_of_stock_products),
        ]

        low_items, low_total = await get_low_stock_products(
            db, threshold=5, skip=0, limit=10
        )
        out_items, out_total = await get_out_of_stock_products(db, skip=0, limit=10)

        assert low_total == 2
        assert len(low_items) == 2
        assert all(0 < p.stock <= 5 for p in low_items)

        assert out_total == 1
        assert len(out_items) == 1
        assert all(p.stock == 0 for p in out_items)
