"""HTTP authentication: JWT access tokens and the current-user dependency."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.api.constants import APIMessages, HTTPStatusCodes
from app.api.deps import get_uow
from app.application.auth import get_user_by_public_id
from app.application.ports import UnitOfWork
from app.domain.user import User
from app.infrastructure.config import settings
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


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


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    uow: UnitOfWork = Depends(get_uow),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Extracts and validates JWT token from Authorization header,
    then retrieves the user from database.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        uow: Unit of work

    Returns:
        Current authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found

    Usage:
        @app.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user": current_user.email}
    """
    token = credentials.credentials

    # Decode JWT token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=HTTPStatusCodes.UNAUTHORIZED,
            detail=APIMessages.TOKEN_INVALID,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user information from token
    user_id: Optional[str] = payload.get("user_id")
    email: Optional[str] = payload.get("sub")

    if user_id is None or email is None:
        logger.warning("Token missing user information")
        raise HTTPException(
            status_code=HTTPStatusCodes.UNAUTHORIZED,
            detail=APIMessages.TOKEN_INVALID,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    try:
        user = await get_user_by_public_id(uow, user_id)
        if user is None:
            logger.warning("User not found for token subject")
            raise HTTPException(
                status_code=HTTPStatusCodes.UNAUTHORIZED,
                detail=APIMessages.UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            logger.warning("Inactive user attempted access")
            raise HTTPException(
                status_code=HTTPStatusCodes.FORBIDDEN,
                detail=APIMessages.USER_INACTIVE,
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("User authenticated via token")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user from token: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            detail=APIMessages.INTERNAL_ERROR,
        )
