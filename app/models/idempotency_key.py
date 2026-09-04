"""Database model for persisted idempotency keys."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


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

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    key = Column(String(128), nullable=False, index=True)
    operation = Column(String(100), nullable=False, index=True)
    request_hash = Column(String(64), nullable=False)
    principal_id = Column(String(36), nullable=True, index=True)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
