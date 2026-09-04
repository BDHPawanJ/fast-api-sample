"""Opaque cursor encoding/decoding helpers for cursor pagination."""

import base64
import hashlib
import hmac
import json
from typing import Optional

from app.core.config import settings


def encode_cursor(last_seen_id: int) -> str:
    """
    Encode cursor payload with signature to prevent tampering.

    Args:
        last_seen_id: Last seen internal numeric identifier.

    Returns:
        str: Opaque, signed cursor string.
    """
    payload = {"last_id": last_seen_id}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = json.dumps({"p": payload, "s": signature}, separators=(",", ":"))
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> Optional[int]:
    """
    Decode and verify an opaque cursor token.

    Args:
        cursor: Opaque cursor token from the client.

    Returns:
        Optional[int]: Last seen internal ID if token is valid, else None.
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        payload = data["p"]
        signature = data["s"]

        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        return int(payload["last_id"])
    except Exception:
        return None
