"""Unit tests for product use cases against an in-memory unit of work."""

from decimal import Decimal

import pytest

from app.application.use_cases.products import (
    create_product,
    delete_product,
    get_all_products,
    get_low_stock_products,
    get_out_of_stock_products,
    get_product_by_id,
    get_product_by_public_id,
    get_products_by_cursor,
    search_products,
    update_product,
)
from app.domain.errors import InvalidProduct
from app.domain.product import Product
from tests.fakes import FakeUnitOfWork
from tests.helpers import must


@pytest.mark.asyncio
class TestProductService:
    """Product service behavior tests."""

    async def test_create_get_update_delete_product(self):
        """Should execute core CRUD operations successfully."""
        uow = FakeUnitOfWork()

        created = await create_product(
            uow,
            name="Laptop",
            description="gaming laptop",
            price=Decimal("1000.0"),
            stock=10,
        )
        assert created.id is not None
        assert uow.commits == 1

        assert must(await get_product_by_id(uow, created.id)).name == "Laptop"

        updated = must(
            await update_product(
                uow,
                created.public_id,
                {"name": "Laptop Pro", "price": Decimal("1200.00")},
            )
        )
        assert (updated.name, updated.price) == ("Laptop Pro", Decimal("1200.00"))
        stored = must(await get_product_by_public_id(uow, created.public_id))
        assert (stored.name, stored.price, stored.stock) == (
            "Laptop Pro",
            Decimal("1200.00"),
            10,
        )

        assert await delete_product(uow, created.public_id) is True
        assert await get_product_by_public_id(uow, created.public_id) is None

    async def test_update_and_delete_non_existent_product(self):
        """Should return None/False for missing products without committing."""
        uow = FakeUnitOfWork()

        assert await update_product(uow, "missing", {"name": "x"}) is None
        assert await delete_product(uow, "missing") is False
        assert not uow.committed

    async def test_update_rejects_invalid_change(self):
        """Explicit null name violates invariants and is not committed."""
        product = Product(name="Laptop", price=Decimal("10.0"))
        uow = FakeUnitOfWork(products=[product])

        with pytest.raises(InvalidProduct):
            await update_product(uow, product.public_id, {"name": None})
        assert not uow.committed
        assert must(await get_product_by_id(uow, must(product.id))).name == "Laptop"

    async def test_cursor_pagination(self):
        """Should page by id and honour search."""
        uow = FakeUnitOfWork(
            products=[
                Product(name=f"Item {i}", price=Decimal("1.0")) for i in range(1, 6)
            ]
        )

        first = await get_products_by_cursor(uow, limit=2)
        second = await get_products_by_cursor(uow, limit=2, cursor_last_id=first[-1].id)
        found = await get_products_by_cursor(uow, limit=10, search="item 3")

        assert [p.name for p in first] == ["Item 1", "Item 2"]
        assert [p.name for p in second] == ["Item 3", "Item 4"]
        assert [p.name for p in found] == ["Item 3"]

    async def test_get_all_products_and_search(self):
        """Should list and search products with pagination."""
        uow = FakeUnitOfWork(
            products=[
                Product(
                    name="MacBook", description="Apple laptop", price=Decimal("2000.0")
                ),
                Product(
                    name="ThinkPad",
                    description="Business laptop",
                    price=Decimal("1500.0"),
                ),
                Product(name="Mouse", description="Wireless", price=Decimal("20.0")),
            ]
        )

        listed, total_listed = await get_all_products(uow, limit=2)
        matched, total_matched = await search_products(uow, "laptop", limit=10)

        assert total_listed == 3
        assert len(listed) == 2
        assert total_matched == 2
        assert {p.name for p in matched} == {"MacBook", "ThinkPad"}

    async def test_low_stock_and_out_of_stock_queries(self):
        """Should return correct low and out-of-stock product sets."""
        uow = FakeUnitOfWork(
            products=[
                Product(name="LowFive", price=Decimal("20.0"), stock=5),
                Product(name="LowOne", price=Decimal("10.0"), stock=1),
                Product(name="Out", price=Decimal("30.0"), stock=0),
                Product(name="Plenty", price=Decimal("30.0"), stock=100),
            ]
        )

        low_items, low_total = await get_low_stock_products(uow, threshold=5, limit=10)
        out_items, out_total = await get_out_of_stock_products(uow, limit=10)

        assert low_total == 2
        assert [p.name for p in low_items] == ["LowOne", "LowFive"]
        assert out_total == 1
        assert [p.name for p in out_items] == ["Out"]
