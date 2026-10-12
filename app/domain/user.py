"""User entity for authentication."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False)
class User:
    """
    Registered user account.

    Password hashing happens outside the domain; this entity only stores the
    resulting hash. ``id`` is None until the user is added to a repository.

    Emails are case-insensitive: they are stored lowercased, so the unique
    index on ``email`` rejects ``User@x.com`` when ``user@x.com`` exists.
    """

    email: str
    hashed_password: str
    is_active: bool = True
    public_id: str = field(default_factory=lambda: str(uuid4()))
    id: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.email = self.normalize_email(self.email)

    @staticmethod
    def normalize_email(email: str) -> str:
        """Canonical form used for storage and lookups."""
        return email.strip().lower()

    def activate(self) -> None:
        """Allow the user to authenticate."""
        self.is_active = True

    def deactivate(self) -> None:
        """Prevent the user from authenticating."""
        self.is_active = False
