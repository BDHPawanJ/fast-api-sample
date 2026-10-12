"""Composition root: FastAPI dependencies that plug adapters into the ports.

This is the only API module that constructs infrastructure. Routes ask for
ports (``UnitOfWork``, ``PasswordHasher``) and tests swap them through
``app.dependency_overrides``.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import PasswordHasher, UnitOfWork
from app.infrastructure.db.session import get_db
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.security.password import BcryptPasswordHasher

__all__ = ["get_db", "get_password_hasher", "get_uow"]

_password_hasher = BcryptPasswordHasher()


def get_uow(db: AsyncSession = Depends(get_db)) -> UnitOfWork:
    """
    Build a unit of work over the request's database session.

    FastAPI caches dependencies per request, so every ``Depends(get_uow)`` in
    one request shares the same session.

    Args:
        db: Request-scoped database session.

    Returns:
        UnitOfWork: SQLAlchemy-backed unit of work.
    """
    return SqlAlchemyUnitOfWork(db)


def get_password_hasher() -> PasswordHasher:
    """
    Provide the application's password hasher.

    Returns:
        PasswordHasher: Shared bcrypt hasher (stateless, safe to reuse).
    """
    return _password_hasher
