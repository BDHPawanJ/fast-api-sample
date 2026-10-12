"""Integration tests for SQLAlchemy repositories against the test database."""

from decimal import Decimal

import pytest

from app.application.idempotency import Outcome, run_idempotent
from app.application.use_cases.cart import add_to_cart
from app.application.use_cases.products import create_product
from app.domain.cart import Cart
from app.domain.errors import EmailAlreadyRegistered
from app.domain.product import Product
from app.domain.user import User
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tests.helpers import must


async def _add_products(uow: SqlAlchemyUnitOfWork, *stocks: int) -> list[Product]:
    products = [
        Product(name=f"P{i}", price=Decimal("1.0"), stock=s)
        for i, s in enumerate(stocks)
    ]
    async with uow:
        for product in products:
            await uow.products.add(product)
        await uow.commit()
    return products


@pytest.mark.integration
@pytest.mark.asyncio
class TestProductRepository:
    async def test_add_assigns_db_generated_fields(self, uow: SqlAlchemyUnitOfWork):
        (product,) = await _add_products(uow, 5)

        assert product.id is not None
        assert product.created_at is not None
        loaded = must(await uow.products.get_by_public_id(product.public_id))
        assert (loaded.id, loaded.name, loaded.stock) == (product.id, "P0", 5)
        assert loaded is not product

    async def test_save_persists_changes(self, uow: SqlAlchemyUnitOfWork):
        (product,) = await _add_products(uow, 5)

        product.update_details(stock=0)
        async with uow:
            await uow.products.save(product)
            await uow.commit()

        (out_of_stock, total) = await uow.products.list_out_of_stock(offset=0, limit=10)
        assert total == 1
        assert out_of_stock[0].id == product.id

    async def test_price_round_trips_exactly(self, uow: SqlAlchemyUnitOfWork):
        product = Product(name="Cable", price=Decimal("0.10"))
        async with uow:
            await uow.products.add(product)
            await uow.commit()

        uow.session.expunge_all()
        loaded = await uow.products.get_by_public_id(product.public_id)
        assert loaded is not None
        assert loaded.price == Decimal("0.10")
        assert isinstance(loaded.price, Decimal)

    async def test_rollback_on_exception(self, uow: SqlAlchemyUnitOfWork):
        with pytest.raises(RuntimeError):
            async with uow:
                await uow.products.add(Product(name="ghost", price=Decimal("1.0")))
                raise RuntimeError("boom")

        assert await uow.products.list_after(limit=10, after_id=None, search=None) == []


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserRepository:
    async def test_duplicate_email_maps_to_domain_error(
        self, uow: SqlAlchemyUnitOfWork
    ):
        async with uow:
            await uow.users.add(User(email="dup@example.com", hashed_password="h"))
            await uow.commit()

        with pytest.raises(EmailAlreadyRegistered):
            async with uow:
                await uow.users.add(User(email="dup@example.com", hashed_password="h"))


@pytest.mark.integration
@pytest.mark.asyncio
class TestCartRepository:
    async def _user_id(self, uow: SqlAlchemyUnitOfWork) -> int:
        user = User(email="cart@example.com", hashed_password="h")
        async with uow:
            await uow.users.add(user)
            await uow.commit()
        return must(user.id)

    async def test_save_syncs_added_updated_and_removed_lines(
        self, uow: SqlAlchemyUnitOfWork
    ):
        user_id = await self._user_id(uow)
        a, b, c = await _add_products(uow, 10, 10, 10)

        cart = Cart(user_id=user_id)
        cart.add_item(a, 1)
        cart.add_item(b, 2)
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()
        assert cart.id is not None

        cart = must(await uow.carts.get_for_user(user_id))
        cart.set_quantity(a, 5)  # update
        cart.remove_item(must(b.id))  # delete
        cart.add_item(c, 3)  # insert
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()

        uow.session.expunge_all()  # force a fresh load from the database
        stored = must(await uow.carts.get_for_user(user_id))
        assert {(i.product_id, i.quantity) for i in stored.items} == {
            (a.id, 5),
            (c.id, 3),
        }

    async def test_remove_then_readd_same_product(self, uow: SqlAlchemyUnitOfWork):
        user_id = await self._user_id(uow)
        (a,) = await _add_products(uow, 10)

        cart = Cart(user_id=user_id)
        cart.add_item(a, 1)
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()

        # Must update the stored line, not delete + insert (unique cart/product).
        cart.remove_item(must(a.id))
        cart.add_item(a, 4)
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()

        uow.session.expunge_all()
        stored = must(await uow.carts.get_for_user(user_id))
        assert [(i.product_id, i.quantity) for i in stored.items] == [(a.id, 4)]

    async def test_clear_deletes_all_lines(self, uow: SqlAlchemyUnitOfWork):
        user_id = await self._user_id(uow)
        a, b = await _add_products(uow, 10, 10)
        cart = Cart(user_id=user_id)
        cart.add_item(a)
        cart.add_item(b)
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()

        cart.clear()
        async with uow:
            await uow.carts.save(cart)
            await uow.commit()

        uow.session.expunge_all()
        assert must(await uow.carts.get_for_user(user_id)).is_empty


@pytest.mark.integration
@pytest.mark.asyncio
class TestIdempotentTransaction:
    async def test_product_and_record_commit_together(self, uow: SqlAlchemyUnitOfWork):
        async def action() -> Outcome:
            product = await create_product(uow, name="Atomic", price=Decimal("1.0"))
            return 201, {"product_id": product.public_id}

        result = await run_idempotent(
            uow, key="k", operation="op", principal_id=None, payload={}, action=action
        )

        uow.session.expunge_all()
        record = await uow.idempotency.get(key="k", operation="op", principal_id=None)
        assert record is not None
        assert await uow.products.get_by_public_id(result.body["product_id"])

    async def test_failure_after_write_rolls_back_product(
        self, uow: SqlAlchemyUnitOfWork
    ):
        async def action() -> Outcome:
            await create_product(uow, name="Orphan", price=Decimal("1.0"))
            raise RuntimeError("crash before the idempotency record is saved")

        with pytest.raises(RuntimeError):
            await run_idempotent(
                uow,
                key="k",
                operation="op",
                principal_id=None,
                payload={},
                action=action,
            )

        products, total = await uow.products.list_newest(offset=0, limit=10)
        assert (products, total) == ([], 0)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCartConflictRetry:
    async def test_lost_race_on_cart_creation_is_retried_and_merged(
        self, uow: SqlAlchemyUnitOfWork, monkeypatch: pytest.MonkeyPatch
    ):
        user = User(email="race@example.com", hashed_password="h")
        async with uow:
            await uow.users.add(user)
            await uow.commit()
        assert user.id is not None
        mouse, laptop = await _add_products(uow, 10, 10)

        # The "other request": creates the cart with a mouse and commits.
        await add_to_cart(uow, user.id, mouse.public_id, 1)

        # Our request read the cart before that commit, so its first read
        # saw no cart; later reads see the real one.
        real_get = uow.carts.get_for_user
        reads = []

        async def stale_first_read(user_id: int):
            reads.append(user_id)
            return None if len(reads) == 1 else await real_get(user_id)

        monkeypatch.setattr(uow.carts, "get_for_user", stale_first_read)

        cart = await add_to_cart(uow, user.id, laptop.public_id, 2)

        assert len(reads) == 2  # first attempt hit uq user_id, retry succeeded
        uow.session.expunge_all()
        stored = await real_get(user.id)
        assert stored is not None
        assert {(i.product_id, i.quantity) for i in stored.items} == {
            (mouse.id, 1),
            (laptop.id, 2),
        }
        assert stored.id == cart.id
