"""In-memory implementations of the application ports for unit tests."""

import copy
from datetime import datetime, timezone
from itertools import count

from app.application.errors import ConcurrencyConflict
from app.application.unit_of_work import TransactionalUnitOfWork
from app.domain.cart import Cart
from app.domain.errors import EmailAlreadyRegistered
from app.domain.idempotency import IdempotencyRecord
from app.domain.product import Product
from app.domain.user import User
from tests.helpers import must


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeProductRepository:
    def __init__(self, products: list[Product] | None = None):
        self._ids = count(1)
        self._rows: dict[int, Product] = {}
        for product in products or []:
            self._store(product)

    async def get(self, product_id: int) -> Product | None:
        return self._copy(self._rows.get(product_id))

    async def get_by_public_id(self, public_id: str) -> Product | None:
        return self._copy(
            next((p for p in self._rows.values() if p.public_id == public_id), None)
        )

    async def add(self, product: Product) -> None:
        self._store(product)

    async def save(self, product: Product) -> None:
        product.updated_at = _now()
        self._rows[must(product.id)] = copy.deepcopy(product)

    async def delete(self, product: Product) -> None:
        self._rows.pop(must(product.id), None)

    async def list_after(
        self, *, limit: int, after_id: int | None, search: str | None
    ) -> list[Product]:
        rows = sorted(self._matching(search), key=lambda p: must(p.id))
        rows = [p for p in rows if after_id is None or must(p.id) > after_id]
        return rows[:limit]

    async def list_newest(
        self, *, offset: int, limit: int, search: str | None = None
    ) -> tuple[list[Product], int]:
        rows = sorted(self._matching(search), key=lambda p: must(p.id), reverse=True)
        return rows[offset : offset + limit], len(rows)

    async def list_low_stock(
        self, *, threshold: int, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        rows = sorted(
            (p for p in self._matching(None) if p.is_low_stock(threshold)),
            key=lambda p: p.stock,
        )
        return rows[offset : offset + limit], len(rows)

    async def list_out_of_stock(
        self, *, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        rows = [p for p in self._matching(None) if not p.is_in_stock]
        return rows[offset : offset + limit], len(rows)

    def _store(self, product: Product) -> None:
        product.id = product.id or next(self._ids)
        product.created_at = product.updated_at = _now()
        self._rows[product.id] = copy.deepcopy(product)

    def _matching(self, search: str | None) -> list[Product]:
        needle = (search or "").lower()
        return [
            copy.deepcopy(p)
            for p in self._rows.values()
            if needle in p.name.lower() or needle in (p.description or "").lower()
        ]

    @staticmethod
    def _copy(product: Product | None) -> Product | None:
        return copy.deepcopy(product) if product else None


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None):
        self._ids = count(1)
        self._rows: dict[int, User] = {}
        for user in users or []:
            self._store(user)

    async def get(self, user_id: int) -> User | None:
        return copy.deepcopy(self._rows.get(user_id))

    async def get_by_public_id(self, public_id: str) -> User | None:
        return self._find(lambda u: u.public_id == public_id)

    async def get_by_email(self, email: str) -> User | None:
        normalized = User.normalize_email(email)
        return self._find(lambda u: u.email == normalized)

    async def add(self, user: User) -> None:
        if self._find(lambda u: u.email == user.email):
            raise EmailAlreadyRegistered(f"Email {user.email} already registered")
        self._store(user)

    async def save(self, user: User) -> None:
        user.updated_at = _now()
        self._rows[must(user.id)] = copy.deepcopy(user)

    def _store(self, user: User) -> None:
        user.id = user.id or next(self._ids)
        user.created_at = user.updated_at = _now()
        self._rows[user.id] = copy.deepcopy(user)

    def _find(self, predicate) -> User | None:
        return copy.deepcopy(next(filter(predicate, self._rows.values()), None))


class FakeCartRepository:
    def __init__(self):
        self._ids = count(1)
        self._rows: dict[int, Cart] = {}
        # Number of upcoming saves that fail as if a concurrent writer won.
        self.conflicts_to_raise = 0
        self.saves_attempted = 0

    async def get_for_user(self, user_id: int) -> Cart | None:
        return copy.deepcopy(self._rows.get(user_id))

    async def save(self, cart: Cart) -> None:
        self.saves_attempted += 1
        if self.conflicts_to_raise > 0:
            self.conflicts_to_raise -= 1
            raise ConcurrencyConflict("simulated concurrent write")
        cart.id = cart.id or next(self._ids)
        self._rows[cart.user_id] = copy.deepcopy(cart)


class FakeIdempotencyRepository:
    def __init__(self):
        self._rows: dict[tuple, IdempotencyRecord] = {}

    async def get(
        self, *, key: str, operation: str, principal_id: str | None
    ) -> IdempotencyRecord | None:
        return self._rows.get((key, operation, principal_id))

    async def add(self, record: IdempotencyRecord) -> None:
        self._rows[(record.key, record.operation, record.principal_id)] = record


class FakePasswordHasher:
    """Reversible, instant stand-in for bcrypt."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed:{password}"


class FakeUnitOfWork(TransactionalUnitOfWork):
    """
    Unit of work with in-memory repositories.

    Shares the real nesting semantics (``commits`` counts only commits that
    reach the outermost block). Repositories store deep copies, like the
    SQLAlchemy adapters return detached snapshots, so a test catches use cases
    that forget to ``save``. Rollback does not undo writes; assert on
    ``committed`` / ``rollbacks`` instead.
    """

    def __init__(
        self,
        *,
        products: list[Product] | None = None,
        users: list[User] | None = None,
    ):
        super().__init__()
        self.products = FakeProductRepository(products)
        self.users = FakeUserRepository(users)
        self.carts = FakeCartRepository()
        self.idempotency = FakeIdempotencyRepository()
        self.commits = 0
        self.rollbacks = 0

    @property
    def committed(self) -> bool:
        return self.commits > 0

    async def _commit(self) -> None:
        self.commits += 1

    async def _rollback(self) -> None:
        self.rollbacks += 1
