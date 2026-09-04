"""FastAPI dependencies for authentication and authorization."""

from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import APIMessages, HTTPStatusCodes
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_public_id as get_user_by_id
from app.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Extracts and validates JWT token from Authorization header,
    then retrieves the user from database.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        db: Database session

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
        user = await get_user_by_id(db, user_id)
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
