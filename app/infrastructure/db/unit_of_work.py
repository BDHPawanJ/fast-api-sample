"""SQLAlchemy unit of work owning the transaction for a use case."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.unit_of_work import TransactionalUnitOfWork
from app.infrastructure.db.repositories.cart import SqlAlchemyCartRepository
from app.infrastructure.db.repositories.idempotency import (
    SqlAlchemyIdempotencyRepository,
)
from app.infrastructure.db.repositories.product import SqlAlchemyProductRepository
from app.infrastructure.db.repositories.user import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(TransactionalUnitOfWork):
    """Unit of work wrapping a request-scoped AsyncSession."""

    def __init__(self, session: AsyncSession):
        super().__init__()
        self.session = session
        self.products = SqlAlchemyProductRepository(session)
        self.users = SqlAlchemyUserRepository(session)
        self.carts = SqlAlchemyCartRepository(session)
        self.idempotency = SqlAlchemyIdempotencyRepository(session)

    async def _commit(self) -> None:
        await self.session.commit()

    async def _rollback(self) -> None:
        await self.session.rollback()
