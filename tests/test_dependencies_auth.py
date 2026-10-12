"""Unit tests for authentication dependencies."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.auth import create_access_token, get_current_user
from app.api.constants import APIMessages, HTTPStatusCodes
from app.domain.user import User
from tests.fakes import FakeUnitOfWork


def _auth_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _token_for(user: User) -> str:
    return create_access_token({"sub": user.email, "user_id": user.public_id})


@pytest.mark.asyncio
class TestGetCurrentUserDependency:
    """Tests for get_current_user dependency."""

    async def test_valid_token_and_active_user(self):
        """Should return user when token and user are valid."""
        user = User(email="user@example.com", hashed_password="hash")
        uow = FakeUnitOfWork(users=[user])

        result = await get_current_user(_auth_credentials(_token_for(user)), uow=uow)
        assert result.id == user.id

    async def test_invalid_token_raises_401(self):
        """Invalid token should raise HTTP 401."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                _auth_credentials("invalid.token"), uow=FakeUnitOfWork()
            )

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.TOKEN_INVALID

    async def test_token_missing_claims_raises_401(self):
        """Token missing required claims should raise HTTP 401."""
        token = create_access_token({"sub": "only-email@example.com"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(token), uow=FakeUnitOfWork())

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.TOKEN_INVALID

    async def test_user_not_found_raises_401(self):
        """Missing user in DB should raise HTTP 401."""
        ghost = User(email="ghost@example.com", hashed_password="hash")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                _auth_credentials(_token_for(ghost)), uow=FakeUnitOfWork()
            )

        assert exc.value.status_code == HTTPStatusCodes.UNAUTHORIZED
        assert exc.value.detail == APIMessages.UNAUTHORIZED

    async def test_inactive_user_raises_403(self):
        """Inactive users should be rejected."""
        user = User(
            email="inactive@example.com", hashed_password="hash", is_active=False
        )
        uow = FakeUnitOfWork(users=[user])

        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(_token_for(user)), uow=uow)

        assert exc.value.status_code == HTTPStatusCodes.FORBIDDEN
        assert exc.value.detail == APIMessages.USER_INACTIVE

    async def test_unexpected_db_error_raises_500(self):
        """Unexpected lookup errors should map to HTTP 500."""
        user = User(email="error@example.com", hashed_password="hash")
        uow = FakeUnitOfWork()
        uow.users.get_by_public_id = AsyncMock(side_effect=RuntimeError("db failure"))

        with pytest.raises(HTTPException) as exc:
            await get_current_user(_auth_credentials(_token_for(user)), uow=uow)

        assert exc.value.status_code == HTTPStatusCodes.INTERNAL_SERVER_ERROR
        assert exc.value.detail == APIMessages.INTERNAL_ERROR
