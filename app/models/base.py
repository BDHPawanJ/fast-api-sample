"""Base model with common fields for all database models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from app.db.base import Base


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

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key identifier",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        doc="Timestamp of record creation",
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
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
