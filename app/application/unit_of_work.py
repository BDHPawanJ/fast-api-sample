"""Nesting-aware transaction handling shared by unit of work implementations."""

from typing import Self


class NestedUnitOfWorkFailed(RuntimeError):
    """An inner block failed, so the outer transaction can only roll back."""


class TransactionalUnitOfWork:
    """
    Base class giving units of work nested-transaction semantics.

    Only the outermost ``async with`` block owns the transaction. A use case
    that commits inside another use case's block (for example, product
    creation wrapped by idempotency handling) has its ``commit()`` deferred, so
    both are persisted atomically by the outer commit.

    If a nested block exits with an exception, the transaction is marked
    rollback-only: committing it later raises ``NestedUnitOfWorkFailed``
    instead of persisting a half-done operation.

    Subclasses implement ``_commit`` and ``_rollback``.
    """

    def __init__(self) -> None:
        self._depth = 0
        self._rollback_only = False

    async def __aenter__(self) -> Self:
        if self._depth == 0:
            self._rollback_only = False
        self._depth += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._depth -= 1
        if exc_type is None:
            return
        if self._depth == 0:
            await self.rollback()
        else:
            self._rollback_only = True

    async def commit(self) -> None:
        """Commit, unless an outer block owns the transaction."""
        if self._depth > 1:
            return
        if self._rollback_only:
            await self.rollback()
            raise NestedUnitOfWorkFailed("A nested unit of work failed")
        await self._commit()

    async def rollback(self) -> None:
        """Roll back the whole transaction, including any outer block's work."""
        await self._rollback()

    async def _commit(self) -> None:
        raise NotImplementedError

    async def _rollback(self) -> None:
        raise NotImplementedError
