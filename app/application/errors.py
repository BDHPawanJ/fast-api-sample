"""Application-level errors that ports may raise."""


class ConcurrencyConflict(Exception):
    """
    A write lost a race with a concurrent transaction.

    Raised by repositories when the database rejects a write because another
    transaction changed the same data first. The operation is safe to retry in
    a new transaction.
    """


class IdempotencyKeyReused(Exception):
    """An idempotency key was reused with a different request payload."""
