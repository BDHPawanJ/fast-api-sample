"""Idempotent execution of retry-safe operations (e.g. POST requests)."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from app.application.errors import IdempotencyKeyReused
from app.application.ports import UnitOfWork
from app.domain.idempotency import IdempotencyRecord

# The action's outcome as it should be replayed: (status code, JSON body).
Outcome = tuple[int, dict[str, Any]]


@dataclass(frozen=True)
class IdempotentResult:
    """Outcome of an idempotent operation, fresh or replayed."""

    status: int
    body: dict[str, Any]
    replayed: bool


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


async def run_idempotent(
    uow: UnitOfWork,
    *,
    key: str,
    operation: str,
    principal_id: Optional[str],
    payload: dict,
    action: Callable[[], Awaitable[Outcome]],
) -> IdempotentResult:
    """
    Run ``action`` once per idempotency key, replaying its outcome on retries.

    The action and the stored idempotency record are committed in one
    transaction, so a crash can never leave one without the other. ``action``
    may call use cases that open their own unit of work blocks; their commits
    are deferred to this one.

    Args:
        uow: Unit of work shared with ``action``.
        key: Idempotency-Key header value.
        operation: Stable operation identifier.
        principal_id: Caller scope identifier.
        payload: Request payload; a retry must send the same payload.
        action: Performs the operation and returns ``(status, body)``.

    Returns:
        IdempotentResult: The fresh or replayed outcome.

    Raises:
        IdempotencyKeyReused: The key was used before with a different payload.
    """
    payload_hash = request_hash(payload)
    async with uow:
        record = await uow.idempotency.get(
            key=key, operation=operation, principal_id=principal_id
        )
        if record is not None:
            if record.request_hash != payload_hash:
                raise IdempotencyKeyReused(
                    "The same Idempotency-Key was reused with a different payload."
                )
            return IdempotentResult(
                status=record.response_status,
                body=json.loads(record.response_body),
                replayed=True,
            )

        status, body = await action()
        await uow.idempotency.add(
            IdempotencyRecord(
                key=key,
                operation=operation,
                principal_id=principal_id,
                request_hash=payload_hash,
                response_status=status,
                response_body=json.dumps(body, separators=(",", ":"), sort_keys=True),
            )
        )
        await uow.commit()

    return IdempotentResult(status=status, body=body, replayed=False)
