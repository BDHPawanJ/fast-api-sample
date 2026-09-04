"""Security utilities for password hashing and JWT token management."""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing context using bcrypt
# Truncate password to 72 bytes automatically
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,  # Don't raise error, truncate automatically
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = get_password_hash("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a plain password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password string

    Example:
        >>> hashed = get_password_hash("mypassword")
        >>> len(hashed) > 50  # Bcrypt hashes are long
        True

    Note:
        Bcrypt has a maximum password length of 72 bytes.
        Longer passwords are automatically truncated.
    """
    try:
        # Manually truncate to 72 bytes for bcrypt compatibility
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            # Truncate to 72 bytes
            password_bytes = password_bytes[:72]
            # Decode back, handling potential encoding issues at boundary
            try:
                password = password_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # If truncation cuts a multi-byte character, try 71, 70, 69...
                for i in range(71, 60, -1):
                    try:
                        password = password_bytes[:i].decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        continue
            logger.debug("Password truncated to 72 bytes for bcrypt")

        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise ValueError(f"Failed to hash password: {str(e)}")


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode in token
        expires_delta: Optional custom expiration time delta

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token(
        ...     data={"sub": "user@example.com", "user_id": 1}
        ... )
        >>> len(token) > 100  # JWT tokens are long
        True
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Encode JWT token
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        logger.debug(f"Access token created for: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary containing token payload if valid, None otherwise

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_access_token(token)
        >>> payload["sub"]
        'user@example.com'
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        logger.debug(f"Token decoded for: {payload.get('sub', 'unknown')}")
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {str(e)}")
        return None


def verify_token(token: str) -> bool:
    """
    Verify if a JWT token is valid.

    Args:
        token: JWT token string to verify

    Returns:
        True if token is valid, False otherwise

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> verify_token(token)
        True
        >>> verify_token("invalid.token.string")
        False
    """
    payload = decode_access_token(token)
    return payload is not None


def extract_user_from_token(token: str) -> Optional[dict]:
    """
    Extract user information from JWT token.

    Args:
        token: JWT token string

    Returns:
        Dictionary with user_id and email if valid, None otherwise

    Example:
        >>> token = create_access_token(
        ...     {"sub": "user@example.com", "user_id": 1}
        ... )
        >>> user_info = extract_user_from_token(token)
        >>> user_info["email"]
        'user@example.com'
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    return {
        "email": payload.get("sub"),
        "user_id": payload.get("user_id"),
    }
