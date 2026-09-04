"""Unit tests for auth service layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import (
    activate_user,
    authenticate_user,
    deactivate_user,
    get_user_by_email,
    get_user_by_id,
    register_user,
)


class _SingleResult:
    """Simple SQLAlchemy-like result wrapper for one object."""

    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _mock_db():
    """Create mocked async DB session."""
    return SimpleNamespace(
        execute=AsyncMock(),
        add=MagicMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
        rollback=AsyncMock(),
    )


@pytest.mark.asyncio
class TestAuthService:
    """Auth service behavior tests."""

    async def test_get_user_by_email_and_id(self):
        """Should return user from query helpers."""
        db = _mock_db()
        user = User(email="service@example.com", hashed_password="hash", is_active=True)
        user.id = 10
        db.execute.side_effect = [_SingleResult(user), _SingleResult(user)]

        found_by_email = await get_user_by_email(db, "service@example.com")
        found_by_id = await get_user_by_id(db, 10)

        assert found_by_email is user
        assert found_by_id is user

    async def test_register_user_success(self, monkeypatch: pytest.MonkeyPatch):
        """Should register a new user when email is not present."""
        db = _mock_db()
        monkeypatch.setattr(
            "app.services.auth_service.get_user_by_email",
            AsyncMock(return_value=None),
        )

        async def set_id(user):
            user.id = 1

        db.refresh.side_effect = set_id

        user = await register_user(
            db,
            UserCreate(email="new-service@example.com", password="ServicePass123"),
        )

        assert user.email == "new-service@example.com"
        assert user.id == 1
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_register_duplicate_email_raises_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Duplicate email should raise ValueError."""
        db = _mock_db()
        existing_user = User(
            email="dup@example.com",
            hashed_password="hash",
            is_active=True,
        )
        monkeypatch.setattr(
            "app.services.auth_service.get_user_by_email",
            AsyncMock(return_value=existing_user),
        )

        with pytest.raises(ValueError):
            await register_user(
                db,
                UserCreate(email="dup@example.com", password="StrongPass123"),
            )

        db.commit.assert_not_awaited()

    async def test_authenticate_user_paths(self, monkeypatch: pytest.MonkeyPatch):
        """Should validate success, wrong password, and inactive cases."""
        db = _mock_db()
        active_user = User(
            email="auth@example.com",
            hashed_password="hash",
            is_active=True,
        )
        active_user.id = 2
        inactive_user = User(
            email="inactive@example.com",
            hashed_password="hash",
            is_active=False,
        )

        monkeypatch.setattr(
            "app.services.auth_service.get_user_by_email",
            AsyncMock(side_effect=[active_user, active_user, None, inactive_user]),
        )
        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            MagicMock(side_effect=[True, False]),
        )

        ok_user = await authenticate_user(db, "auth@example.com", "AuthPass123")
        wrong_password = await authenticate_user(db, "auth@example.com", "WrongPass123")
        unknown_user = await authenticate_user(db, "missing@example.com", "AuthPass123")
        inactive = await authenticate_user(db, "inactive@example.com", "AuthPass123")

        assert ok_user is active_user
        assert wrong_password is None
        assert unknown_user is None
        assert inactive is None

    async def test_deactivate_and_activate_user(self, monkeypatch: pytest.MonkeyPatch):
        """Should toggle active flag and handle missing users."""
        db = _mock_db()
        user = User(email="toggle@example.com", hashed_password="hash", is_active=True)
        user.id = 5

        monkeypatch.setattr(
            "app.services.auth_service.get_user_by_id",
            AsyncMock(side_effect=[user, user, None, None]),
        )

        deactivated = await deactivate_user(db, user.id)
        assert deactivated is not None
        assert deactivated.is_active is False

        activated = await activate_user(db, user.id)
        missing_deactivate = await deactivate_user(db, 999999)
        missing_activate = await activate_user(db, 999999)

        assert activated is not None
        assert activated.is_active is True
        assert missing_deactivate is None
        assert missing_activate is None
