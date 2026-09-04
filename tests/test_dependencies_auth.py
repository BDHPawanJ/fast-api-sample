"""Unit tests for authentication dependencies."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.constants import APIMessages, HTTPStatusCodes
from app.core.security import create_access_token
from app.dependencies.auth import get_current_user
from app.models.user import User


def _auth_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
class TestGetCurrentUserDependency:
    """Tests for get_current_user dependency."""

    async def test_valid_token_and_active_user(self, monkeypatch: pytest.MonkeyPatch):
        """Should return user when token and user are valid."""
        token = create_access_token({"sub": "user@example.com", "user_id": 1})
        user = User(email="user@example.com", hashed_password="hash", is_active=True)
        user.id = 1

        monkeypatch.setattr(
            "app.dependencies.auth.get_user_by_id",
            AsyncMock(return_value=user),
        )

        result = await get_current_user(_auth_credentials(token), db=object())
        assert result.id == 1

    async def test_invalid_token_raises_401(self):
        """Invalid token should raise HTTP 401."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials("invalid.token"), db=object())

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.TOKEN_INVALID

    async def test_token_missing_claims_raises_401(self):
        """Token missing required claims should raise HTTP 401."""
        token = create_access_token({"sub": "only-email@example.com"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(token), db=object())

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.TOKEN_INVALID

    async def test_user_not_found_raises_401(self, monkeypatch: pytest.MonkeyPatch):
        """Missing user in DB should raise HTTP 401."""
        token = create_access_token({"sub": "ghost@example.com", "user_id": 999})
        monkeypatch.setattr(
            "app.dependencies.auth.get_user_by_id",
            AsyncMock(return_value=None),
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(token), db=object())

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.UNAUTHORIZED

    async def test_inactive_user_raises_403(self, monkeypatch: pytest.MonkeyPatch):
        """Inactive users should be rejected."""
        token = create_access_token({"sub": "inactive@example.com", "user_id": 7})
        user = User(
            email="inactive@example.com", hashed_password="hash", is_active=False
        )
        user.id = 7
        monkeypatch.setattr(
            "app.dependencies.auth.get_user_by_id",
            AsyncMock(return_value=user),
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(token), db=object())

        assert exc.value.status_code == HTTPStatusCodes.FORBIDDEN
        assert exc.value.detail == APIMessages.USER_INACTIVE

    async def test_unexpected_db_error_raises_500(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Unexpected lookup errors should map to HTTP 500."""
        token = create_access_token({"sub": "error@example.com", "user_id": 5})
        monkeypatch.setattr(
            "app.dependencies.auth.get_user_by_id",
            AsyncMock(side_effect=RuntimeError("db failure")),
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(token), db=object())

        assert exc.value.status_code == HTTPStatusCodes.INTERNAL_SERVER_ERROR
        assert exc.value.detail == APIMessages.INTERNAL_ERROR
