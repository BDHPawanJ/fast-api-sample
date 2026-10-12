"""Tests for nested unit of work transaction semantics."""

import pytest

from app.application.unit_of_work import NestedUnitOfWorkFailed
from tests.fakes import FakeUnitOfWork


@pytest.mark.asyncio
class TestNestedUnitOfWork:
    async def test_inner_commit_is_deferred_to_outer(self):
        uow = FakeUnitOfWork()
        async with uow:
            async with uow:
                await uow.commit()
            assert uow.commits == 0
            await uow.commit()
        assert uow.commits == 1

    async def test_exception_in_outermost_block_rolls_back(self):
        uow = FakeUnitOfWork()
        with pytest.raises(RuntimeError):
            async with uow:
                raise RuntimeError("boom")
        assert (uow.commits, uow.rollbacks) == (0, 1)

    async def test_failed_inner_block_poisons_outer_commit(self):
        uow = FakeUnitOfWork()
        async with uow:
            with pytest.raises(RuntimeError):
                async with uow:
                    raise RuntimeError("inner failure swallowed by caller")
            with pytest.raises(NestedUnitOfWorkFailed):
                await uow.commit()
        assert (uow.commits, uow.rollbacks) == (0, 1)

    async def test_poison_flag_resets_for_next_transaction(self):
        uow = FakeUnitOfWork()
        async with uow:
            with pytest.raises(RuntimeError):
                async with uow:
                    raise RuntimeError("boom")
            await uow.rollback()

        async with uow:
            await uow.commit()
        assert uow.commits == 1
