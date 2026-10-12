"""Unit tests for JWT access token helpers."""

from datetime import timedelta

from app.api.auth import (
    create_access_token,
    decode_access_token,
    extract_user_from_token,
    verify_token,
)


def test_token_create_decode_verify_and_extract():
    """Valid tokens should decode and expose user details."""
    token = create_access_token(
        {"sub": "user@example.com", "user_id": 7},
        expires_delta=timedelta(minutes=10),
    )

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["user_id"] == 7
    assert verify_token(token) is True

    user_info = extract_user_from_token(token)
    assert user_info == {"email": "user@example.com", "user_id": 7}


def test_decode_invalid_token_returns_none():
    """Invalid token should not decode."""
    assert decode_access_token("invalid.token.value") is None
    assert verify_token("invalid.token.value") is False
    assert extract_user_from_token("invalid.token.value") is None


def test_decode_expired_token_returns_none():
    """Expired token should be treated as invalid."""
    token = create_access_token(
        {"sub": "expired@example.com", "user_id": 9},
        expires_delta=timedelta(seconds=-1),
    )

    assert decode_access_token(token) is None
