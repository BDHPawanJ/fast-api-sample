"""SQLAlchemy-backed idempotency key repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.idempotency import IdempotencyRecord
from app.infrastructure.db.models.idempotency_key import (
    IdempotencyKey as IdempotencyRow,
)


class SqlAlchemyIdempotencyRepository:
    """Idempotency record repository backed by an AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self, *, key: str, operation: str, principal_id: str | None
    ) -> IdempotencyRecord | None:
        row = await self.session.scalar(
            select(IdempotencyRow).where(
                IdempotencyRow.key == key,
                IdempotencyRow.operation == operation,
                IdempotencyRow.principal_id == principal_id,
            )
        )
        if row is None:
            return None
        return IdempotencyRecord(
            key=row.key,
            operation=row.operation,
            principal_id=row.principal_id,
            request_hash=row.request_hash,
            response_status=row.response_status,
            response_body=row.response_body,
        )

    async def add(self, record: IdempotencyRecord) -> None:
        self.session.add(
            IdempotencyRow(
                key=record.key,
                operation=record.operation,
                principal_id=record.principal_id,
                request_hash=record.request_hash,
                response_status=record.response_status,
                response_body=record.response_body,
            )
        )
        await self.session.flush()
