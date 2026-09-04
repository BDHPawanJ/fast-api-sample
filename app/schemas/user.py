"""Pydantic schemas for user authentication and responses."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """
    Base schema for user payloads.

    Attributes:
        email: Valid user email address.
    """

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )


class UserCreate(UserBase):
    """
    Schema for user registration.

    Attributes:
        email: Valid email address
        password: Password with minimum 8 characters
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (minimum 8 characters)",
        examples=["SecurePass123!"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength.

        Args:
            v: Password string

        Returns:
            Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one digit
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")

        # Check for at least one letter
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one letter")

        return v

    class Config:
        """
        Pydantic model configuration for UserCreate schema.

        Attributes:
            json_schema_extra: Example payload for OpenAPI docs.
        """

        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
            }
        }


class UserLogin(UserBase):
    """
    Schema for user login.

    Attributes:
        email: User email address
        password: User password
    """

    password: str = Field(
        ...,
        description="User password",
        examples=["SecurePass123!"],
    )

    class Config:
        """
        Pydantic model configuration for UserLogin schema.

        Attributes:
            json_schema_extra: Example payload for OpenAPI docs.
        """

        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
            }
        }


class UserResponse(UserBase):
    """
    Schema for user data in responses.

    Attributes:
        id: User ID
        email: User email address
        is_active: Account active status
        created_at: Account creation timestamp
    """

    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        """
        Pydantic model configuration for UserResponse schema.

        Attributes:
            from_attributes: Enables ORM object parsing.
            json_schema_extra: Example payload for OpenAPI docs.
        """

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "is_active": True,
                "created_at": "2024-01-01T12:00:00",
            }
        }


class Token(BaseModel):
    """
    Schema for JWT token response.

    Attributes:
        access_token: JWT access token
        token_type: Token type (always "bearer")
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    class Config:
        """
        Pydantic model configuration for Token schema.

        Attributes:
            json_schema_extra: Example payload for OpenAPI docs.
        """

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
