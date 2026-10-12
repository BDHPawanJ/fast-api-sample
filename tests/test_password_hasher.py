"""Tests for the bcrypt PasswordHasher adapter."""

from app.infrastructure.security.password import BcryptPasswordHasher

hasher = BcryptPasswordHasher()


def test_hash_and_verify_round_trip():
    """Hashing and verification should work for a valid password."""
    hashed = hasher.hash("StrongPass123")

    assert hashed != "StrongPass123"
    assert hasher.verify("StrongPass123", hashed) is True
    assert hasher.verify("WrongPass123", hashed) is False


def test_verify_with_invalid_hash_returns_false():
    """Invalid hash format should safely return False."""
    assert hasher.verify("any-password", "not-a-valid-hash") is False


def test_long_password_truncated_on_character_boundary():
    """Passwords over 72 bytes hash as their first 72 bytes, never mid-character."""
    prefix = "a" * 71
    hashed = hasher.hash(prefix + "é" + "tail")  # "é" straddles byte 72

    assert hasher.verify(prefix, hashed) is True
