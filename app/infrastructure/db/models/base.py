"""Base model with common fields for all database models."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.db.base import Base


class BaseModel(Base):
    """
    Abstract base model with common fields.

    All database models should inherit from this class to get
    automatic id, created_at, and updated_at fields.

    Attributes:
        id: Primary key integer ID
        created_at: Timestamp of record creation (auto-generated)
        updated_at: Timestamp of last update (auto-updated)
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key identifier",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        doc="Timestamp of record creation",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        doc="Timestamp of last update",
    )

    def __repr__(self) -> str:
        """
        Return a concise string representation of the model instance.

        Returns:
            str: String containing model class name and primary key.
        """
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
