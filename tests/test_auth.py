"""Tests for authentication endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.user import User


def idempotency_headers() -> dict:
    """Build headers with a fresh Idempotency-Key."""
    return {"Idempotency-Key": str(uuid4())}


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication API endpoints."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
            },
            headers=idempotency_headers(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "user_id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_without_idempotency_key(self, client: AsyncClient):
        """Test registration without Idempotency-Key fails validation."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"

    async def test_register_idempotent_replay(self, client: AsyncClient):
        """Test retrying with the same key and payload replays the response."""
        headers = idempotency_headers()
        payload = {"email": "replay@example.com", "password": "SecurePass123"}

        first = await client.post("/v1/auth/register", json=payload, headers=headers)
        second = await client.post("/v1/auth/register", json=payload, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json() == first.json()

    async def test_register_idempotency_key_reused_with_different_payload(
        self, client: AsyncClient
    ):
        """Test reusing a key with a different payload is rejected."""
        headers = idempotency_headers()

        await client.post(
            "/v1/auth/register",
            json={"email": "first@example.com", "password": "SecurePass123"},
            headers=headers,
        )
        response = await client.post(
            "/v1/auth/register",
            json={"email": "second@example.com", "password": "SecurePass123"},
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["code"] == "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email fails."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "AnotherPass123",
            },
            headers=idempotency_headers(),
        )

        assert response.status_code == 409
        assert response.headers["content-type"] == "application/problem+json"

    async def test_register_duplicate_email_differing_in_case(
        self, client: AsyncClient, test_user: User
    ):
        """Emails are case-insensitive: one account per address."""
        response = await client.post(
            "/v1/auth/register",
            json={"email": test_user.email.upper(), "password": "AnotherPass123"},
            headers=idempotency_headers(),
        )

        assert response.status_code == 409

    async def test_login_email_is_case_insensitive(
        self, client: AsyncClient, test_user: User
    ):
        """Login matches the account regardless of email case."""
        response = await client.post(
            "/v1/auth/login",
            json={"email": test_user.email.upper(), "password": "TestPassword123"},
        )

        assert response.status_code == 200
        assert response.json()["user"]["user_id"] == test_user.public_id

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password fails validation."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak",
            },
            headers=idempotency_headers(),
        )

        assert response.status_code == 422
        fields = [error["field"] for error in response.json()["errors"]]
        assert "body -> password" in fields

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails validation."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
            },
            headers=idempotency_headers(),
        )

        assert response.status_code == 422
        fields = [error["field"] for error in response.json()["errors"]]
        assert "body -> email" in fields

    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email
        assert data["user"]["user_id"] == test_user.public_id

    async def test_login_token_authenticates(
        self, client: AsyncClient, test_user: User
    ):
        """Test the token returned by login can access protected endpoints."""
        login = await client.post(
            "/v1/auth/login",
            json={"email": test_user.email, "password": "TestPassword123"},
        )
        token = login.json()["access_token"]

        response = await client.get(
            "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with non-existent email fails."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401

    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password fails."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401

    async def test_get_current_user_success(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test getting current user info with valid token."""
        response = await client.get("/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["user_id"] == test_user.public_id

    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token fails."""
        response = await client.get("/v1/auth/me")

        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
