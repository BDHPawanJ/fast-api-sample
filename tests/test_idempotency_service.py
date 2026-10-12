"""Unit tests for idempotent execution against an in-memory unit of work."""

from decimal import Decimal

import pytest

from app.application.errors import IdempotencyKeyReused
from app.application.idempotency import Outcome, run_idempotent
from app.application.products import create_product
from tests.fakes import FakeUnitOfWork

PAYLOAD = {"name": "Laptop", "price": 10.0}


async def _run(uow: FakeUnitOfWork, payload: dict = PAYLOAD, calls: list | None = None):
    async def action() -> Outcome:
        if calls is not None:
            calls.append(1)
        product = await create_product(uow, name="Laptop", price=Decimal("10.0"))
        return 201, {"product_id": product.public_id}

    return await run_idempotent(
        uow,
        key="key-1",
        operation="products.create",
        principal_id="user-1",
        payload=payload,
        action=action,
    )


@pytest.mark.asyncio
class TestRunIdempotent:
    async def test_first_call_runs_action_and_commits_once(self):
        uow = FakeUnitOfWork()

        result = await _run(uow)

        assert (result.status, result.replayed) == (201, False)
        # create_product's own commit is deferred into the single outer commit.
        assert uow.commits == 1

    async def test_retry_replays_without_running_action(self):
        uow = FakeUnitOfWork()
        first = await _run(uow)
        calls: list = []

        second = await _run(uow, calls=calls)

        assert calls == []
        assert second.replayed is True
        assert (second.status, second.body) == (first.status, first.body)

    async def test_reused_key_with_different_payload_raises(self):
        uow = FakeUnitOfWork()
        await _run(uow)

        with pytest.raises(IdempotencyKeyReused):
            await _run(uow, payload={**PAYLOAD, "price": 99.0})

    async def test_failing_action_commits_nothing(self):
        uow = FakeUnitOfWork()

        async def action() -> Outcome:
            await create_product(uow, name="Laptop", price=Decimal("10.0"))
            raise RuntimeError("crash after the product was written")

        with pytest.raises(RuntimeError):
            await run_idempotent(
                uow,
                key="k",
                operation="op",
                principal_id=None,
                payload={},
                action=action,
            )
        assert (uow.commits, uow.rollbacks) == (0, 1)
        assert (
            await uow.idempotency.get(key="k", operation="op", principal_id=None)
            is None
        )
