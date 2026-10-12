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
    """

    email: str
    hashed_password: str
    is_active: bool = True
    public_id: str = field(default_factory=lambda: str(uuid4()))
    id: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def activate(self) -> None:
        """Allow the user to authenticate."""
        self.is_active = True

    def deactivate(self) -> None:
        """Prevent the user from authenticating."""
        self.is_active = False
