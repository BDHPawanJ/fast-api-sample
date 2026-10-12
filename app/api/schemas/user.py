"""User request schemas: generated contract models plus custom validation."""

from pydantic import field_validator

from app.api.schemas import generated

UserLogin = generated.UserLogin


class UserCreate(generated.UserCreate):
    # Python does not inherit __doc__; keep the contract's schema description.
    __doc__ = generated.UserCreate.__doc__

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Require at least one digit and one letter in the password.

        Length limits are enforced by the contract (minLength/maxLength).

        Args:
            v: Password string

        Returns:
            Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")

        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one letter")

        return v
