"""Unit tests for cart use cases against an in-memory unit of work."""

from decimal import Decimal

import pytest

from app.application.cart import (
    MAX_ATTEMPTS,
    add_to_cart,
    clear_cart,
    get_cart,
    remove_from_cart,
    update_cart_item,
)
from app.application.errors import ConcurrencyConflict
from app.domain.errors import CartItemNotFound, InsufficientStock, ProductNotFound
from app.domain.product import Product
from tests.fakes import FakeUnitOfWork

USER_ID = 1


@pytest.fixture
def laptop() -> Product:
    return Product(name="Laptop", price=Decimal("999.0"), stock=3)


@pytest.fixture
def uow(laptop: Product) -> FakeUnitOfWork:
    return FakeUnitOfWork(products=[laptop])


@pytest.mark.asyncio
class TestCartService:
    """Cart service behavior tests."""

    async def test_get_cart_without_one_returns_empty_cart(self, uow):
        cart = await get_cart(uow, USER_ID)
        assert cart.is_empty
        assert not uow.committed

    async def test_add_to_cart_persists_and_merges(self, uow, laptop):
        await add_to_cart(uow, USER_ID, laptop.public_id, 1)
        await add_to_cart(uow, USER_ID, laptop.public_id, 2)

        cart = await get_cart(uow, USER_ID)
        assert cart.quantity_of(laptop.id) == 3
        assert uow.commits == 2

    async def test_add_to_cart_insufficient_stock(self, uow, laptop):
        with pytest.raises(InsufficientStock):
            await add_to_cart(uow, USER_ID, laptop.public_id, 4)
        assert not uow.committed

    async def test_add_unknown_product(self, uow):
        with pytest.raises(ProductNotFound):
            await add_to_cart(uow, USER_ID, "missing", 1)

    async def test_update_and_remove(self, uow, laptop):
        await add_to_cart(uow, USER_ID, laptop.public_id, 1)

        await update_cart_item(uow, USER_ID, laptop.public_id, 2)
        assert (await get_cart(uow, USER_ID)).quantity_of(laptop.id) == 2

        await remove_from_cart(uow, USER_ID, laptop.public_id)
        assert (await get_cart(uow, USER_ID)).is_empty

        with pytest.raises(CartItemNotFound):
            await remove_from_cart(uow, USER_ID, laptop.public_id)

    async def test_clear_cart(self, uow, laptop):
        await add_to_cart(uow, USER_ID, laptop.public_id, 1)
        await clear_cart(uow, USER_ID)
        assert (await get_cart(uow, USER_ID)).is_empty

    async def test_conflict_is_retried_in_a_new_transaction(self, uow, laptop):
        uow.carts.conflicts_to_raise = 1

        cart = await add_to_cart(uow, USER_ID, laptop.public_id, 1)

        assert cart.quantity_of(laptop.id) == 1
        assert uow.carts.saves_attempted == 2
        assert (uow.rollbacks, uow.commits) == (1, 1)

    async def test_gives_up_after_max_attempts(self, uow, laptop):
        uow.carts.conflicts_to_raise = MAX_ATTEMPTS

        with pytest.raises(ConcurrencyConflict):
            await add_to_cart(uow, USER_ID, laptop.public_id, 1)
        assert uow.carts.saves_attempted == MAX_ATTEMPTS
        assert not uow.committed
