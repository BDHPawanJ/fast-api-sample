"""Ports: the interfaces the application layer depends on.

Use cases are written against these Protocols; ``app.infrastructure`` provides
the implementations and tests provide in-memory fakes.
"""

from typing import Protocol, Self

from app.domain.cart import Cart
from app.domain.idempotency import IdempotencyRecord
from app.domain.product import Product
from app.domain.user import User


class ProductRepository(Protocol):
    async def get(self, product_id: int) -> Product | None: ...

    async def get_by_public_id(self, public_id: str) -> Product | None: ...

    async def add(self, product: Product) -> None:
        """Persist a new product and assign id/timestamps on it."""
        ...

    async def save(self, product: Product) -> None:
        """Persist changes to an existing product and refresh timestamps."""
        ...

    async def delete(self, product: Product) -> None: ...

    async def list_after(
        self, *, limit: int, after_id: int | None, search: str | None
    ) -> list[Product]:
        """Products ordered by id ascending, starting after ``after_id``."""
        ...

    async def list_newest(
        self, *, offset: int, limit: int, search: str | None = None
    ) -> tuple[list[Product], int]:
        """Products ordered newest first, with the total match count."""
        ...

    async def list_low_stock(
        self, *, threshold: int, offset: int, limit: int
    ) -> tuple[list[Product], int]: ...

    async def list_out_of_stock(
        self, *, offset: int, limit: int
    ) -> tuple[list[Product], int]: ...


class UserRepository(Protocol):
    async def get(self, user_id: int) -> User | None: ...

    async def get_by_public_id(self, public_id: str) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def add(self, user: User) -> None:
        """
        Persist a new user and assign id/timestamps on it.

        Raises:
            EmailAlreadyRegistered: The email is already taken.
        """
        ...

    async def save(self, user: User) -> None: ...


class CartRepository(Protocol):
    async def get_for_user(self, user_id: int) -> Cart | None: ...

    async def save(self, cart: Cart) -> None:
        """
        Insert the cart or sync its lines with what is stored.

        Raises:
            ConcurrencyConflict: A concurrent transaction created the cart or
                one of its lines first. Retry in a new transaction.
        """
        ...


class IdempotencyRepository(Protocol):
    async def get(
        self, *, key: str, operation: str, principal_id: str | None
    ) -> IdempotencyRecord | None: ...

    async def add(self, record: IdempotencyRecord) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed_password: str) -> bool:
        """Return False for a wrong password or a malformed hash."""
        ...


class UnitOfWork(Protocol):
    """
    Transaction boundary for a use case.

    Usage::

        async with uow:
            ...
            await uow.commit()

    Leaving the block because of an exception rolls back. Blocks nest: only
    the outermost one commits, so use cases can be composed into a single
    transaction (see ``TransactionalUnitOfWork``).
    """

    # Read-only properties rather than plain attributes: a mutable Protocol
    # attribute is invariant, so an implementation could not declare a
    # concrete repository type for it.
    @property
    def products(self) -> ProductRepository: ...

    @property
    def users(self) -> UserRepository: ...

    @property
    def carts(self) -> CartRepository: ...

    @property
    def idempotency(self) -> IdempotencyRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
