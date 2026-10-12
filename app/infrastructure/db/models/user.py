"""User model for authentication and authorization."""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from app.infrastructure.db.models.shopping_cart import ShoppingCart


class User(BaseModel):
    """
    User model for storing authentication credentials.

    Attributes:
        id: Primary key (inherited from BaseModel)
        email: Unique email address for authentication
        hashed_password: Bcrypt hashed password
        is_active: Flag indicating if user account is active
        created_at: Timestamp of user creation (inherited from BaseModel)
        updated_at: Timestamp of last update (inherited from BaseModel)
    """

    __tablename__ = "users"

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
        doc="Public UUID identifier for API exposure",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="User email address (unique identifier)",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
        doc="Flag indicating if user account is active",
    )

    cart: Mapped["ShoppingCart | None"] = relationship(
        back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        """
        Return a concise string representation of the user instance.

        Returns:
            str: String containing user identifier and active status.
        """
        return f"<User(id={self.id}, public_id={self.public_id}, is_active={self.is_active})>"
