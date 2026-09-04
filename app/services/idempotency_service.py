"""Service helpers for idempotent POST request processing."""

import hashlib
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey


def request_hash(payload: dict) -> str:
    """
    Build a stable SHA-256 hash from a JSON payload.

    Args:
        payload: JSON-serializable request payload.

    Returns:
        str: Hex digest hash.
    """
    normalized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def get_idempotency_record(
    db: AsyncSession,
    *,
    key: str,
    operation: str,
    principal_id: Optional[str],
) -> Optional[IdempotencyKey]:
    """
    Retrieve an existing idempotency record by scope.

    Args:
        db: Database session.
        key: Idempotency-Key header value.
        operation: Stable operation identifier.
        principal_id: Caller scope identifier.

    Returns:
        Optional[IdempotencyKey]: Existing record if any.
    """
    query = select(IdempotencyKey).where(
        IdempotencyKey.key == key,
        IdempotencyKey.operation == operation,
        IdempotencyKey.principal_id == principal_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def save_idempotency_record(
    db: AsyncSession,
    *,
    key: str,
    operation: str,
    principal_id: Optional[str],
    request_body_hash: str,
    response_status: int,
    response_body: dict,
) -> None:
    """
    Persist idempotency execution output for future retries.

    Args:
        db: Database session.
        key: Idempotency-Key header value.
        operation: Stable operation identifier.
        principal_id: Caller scope identifier.
        request_body_hash: Stable hash of the request body.
        response_status: HTTP status returned for the first request.
        response_body: JSON response body for replay.
    """
    record = IdempotencyKey(
        key=key,
        operation=operation,
        principal_id=principal_id,
        request_hash=request_body_hash,
        response_status=response_status,
        response_body=json.dumps(response_body, separators=(",", ":"), sort_keys=True),
    )
    db.add(record)
    await db.commit()


def decode_response_body(raw_response: str) -> dict:
    """
    Parse persisted idempotency response JSON.

    Args:
        raw_response: Serialized response payload.

    Returns:
        dict: Parsed response payload.
    """
    return json.loads(raw_response)
