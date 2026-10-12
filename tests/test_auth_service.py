"""Unit tests for auth use cases against an in-memory unit of work."""

import pytest

from app.application.auth import (
    activate_user,
    authenticate_user,
    deactivate_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_public_id,
    register_user,
)
from app.domain.errors import EmailAlreadyRegistered
from app.domain.user import User
from tests.fakes import FakePasswordHasher, FakeUnitOfWork
from tests.helpers import must

hasher = FakePasswordHasher()


@pytest.mark.asyncio
class TestAuthService:
    """Auth service behavior tests."""

    async def test_lookups(self):
        """Should find users by email, id, and public id."""
        user = User(email="service@example.com", hashed_password="hash")
        uow = FakeUnitOfWork(users=[user])

        assert must(await get_user_by_email(uow, user.email)).id == user.id
        assert must(await get_user_by_id(uow, must(user.id))).email == user.email
        assert must(await get_user_by_public_id(uow, user.public_id)).id == user.id
        assert await get_user_by_email(uow, "missing@example.com") is None

    async def test_register_user_success(self):
        """Should store a new user with a hashed password."""
        uow = FakeUnitOfWork()

        user = await register_user(
            uow, hasher, email="new@example.com", password="ServicePass123"
        )

        assert user.id is not None
        assert user.is_active is True
        assert hasher.verify("ServicePass123", user.hashed_password)
        assert uow.commits == 1

    async def test_register_duplicate_email_raises(self):
        """Duplicate email should raise and not commit."""
        uow = FakeUnitOfWork(
            users=[User(email="dup@example.com", hashed_password="hash")]
        )

        with pytest.raises(EmailAlreadyRegistered):
            await register_user(
                uow, hasher, email="dup@example.com", password="StrongPass123"
            )
        assert not uow.committed

    async def test_authenticate_user_paths(self):
        """Should validate success, wrong password, unknown, and inactive cases."""
        hashed = hasher.hash("AuthPass123")
        uow = FakeUnitOfWork(
            users=[
                User(email="auth@example.com", hashed_password=hashed),
                User(
                    email="inactive@example.com",
                    hashed_password=hashed,
                    is_active=False,
                ),
            ]
        )

        ok = await authenticate_user(uow, hasher, "auth@example.com", "AuthPass123")
        assert ok is not None and ok.email == "auth@example.com"
        assert (
            await authenticate_user(uow, hasher, "auth@example.com", "Wrong123") is None
        )
        assert await authenticate_user(uow, hasher, "nobody@example.com", "x1") is None
        assert (
            await authenticate_user(uow, hasher, "inactive@example.com", "AuthPass123")
            is None
        )

    async def test_deactivate_and_activate_user(self):
        """Should persist the active flag and handle missing users."""
        user = User(email="toggle@example.com", hashed_password="hash")
        uow = FakeUnitOfWork(users=[user])

        await deactivate_user(uow, user.public_id)
        assert must(await get_user_by_id(uow, must(user.id))).is_active is False

        await activate_user(uow, user.public_id)
        assert must(await get_user_by_id(uow, must(user.id))).is_active is True

        assert await deactivate_user(uow, "missing") is None
        assert await activate_user(uow, "missing") is None
