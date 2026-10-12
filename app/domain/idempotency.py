"""Idempotency record for retry-safe POST operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IdempotencyRecord:
    """Stored outcome of the first execution of an idempotent request."""

    key: str
    operation: str
    principal_id: str | None
    request_hash: str
    response_status: int
    response_body: str
