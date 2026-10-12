"""SQLAlchemy-backed user repository."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import EmailAlreadyRegistered
from app.domain.user import User
from app.infrastructure.db.models.user import User as UserRow


def to_domain(row: UserRow) -> User:
    """Build a domain user from an ORM row."""
    return User(
        id=row.id,
        public_id=row.public_id,
        email=row.email,
        hashed_password=row.hashed_password,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyUserRepository:
    """User repository backed by an AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        row = await self._row(UserRow.id == user_id)
        return to_domain(row) if row else None

    async def get_by_public_id(self, public_id: str) -> User | None:
        row = await self._row(UserRow.public_id == public_id)
        return to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = await self._row(UserRow.email == User.normalize_email(email))
        return to_domain(row) if row else None

    async def add(self, user: User) -> None:
        row = UserRow(
            public_id=user.public_id,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
        )
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError as e:
            raise EmailAlreadyRegistered(
                f"Email {user.email} already registered"
            ) from e
        await self.session.refresh(row)
        user.id = row.id
        user.created_at = row.created_at
        user.updated_at = row.updated_at

    async def save(self, user: User) -> None:
        row = await self._row(UserRow.id == user.id)
        if row is None:
            raise LookupError(f"User {user.public_id} is not persisted")
        row.email = user.email
        row.hashed_password = user.hashed_password
        row.is_active = user.is_active
        await self.session.flush()
        await self.session.refresh(row)
        user.updated_at = row.updated_at

    async def _row(self, criterion) -> UserRow | None:
        return await self.session.scalar(select(UserRow).where(criterion))
