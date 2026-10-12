"""Database model for persisted idempotency keys."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class IdempotencyKey(Base):
    """
    Persisted idempotency key record for retry-safe POST operations.

    Attributes:
        id: Internal primary key.
        key: Client-provided idempotency key value.
        operation: Stable operation identifier.
        request_hash: Hash of normalized request payload.
        principal_id: Caller identifier scope (nullable for public calls).
        response_status: HTTP status from first successful execution.
        response_body: Serialized JSON response body.
        created_at: Record creation timestamp.
    """

    __tablename__ = "idempotency_keys"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=False
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
