"""Authentication service for user registration and login."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieve a user by email address.

    Args:
        db: Database session
        email: User email address

    Returns:
        User object if found, None otherwise

    Example:
        >>> user = await get_user_by_email(db, "user@example.com")
        >>> user.email if user else None
        'user@example.com'
    """
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            logger.debug("User found by email")
        else:
            logger.debug("User not found by email")

        return user
    except Exception as e:
        logger.error(f"Error fetching user by email: {str(e)}")
        raise


async def get_user_by_public_id(db: AsyncSession, public_id: str) -> Optional[User]:
    """
    Retrieve a user by public UUID.

    Args:
        db: Database session
        public_id: User public UUID identifier

    Returns:
        User object if found, None otherwise

    Example:
        >>> user = await get_user_by_public_id(db, "2fd3c267-e366-4cfd-99f4-6be245472585")
        >>> bool(user)
        True
    """
    try:
        result = await db.execute(select(User).where(User.public_id == public_id))
        user = result.scalar_one_or_none()

        if user:
            logger.debug("User found by public_id")
        else:
            logger.debug("User not found by public_id")

        return user
    except Exception as e:
        logger.error(f"Error fetching user by public_id: {str(e)}")
        raise


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Retrieve a user by internal numeric identifier.

    Args:
        db: Database session
        user_id: Internal user ID

    Returns:
        Optional[User]: User if found, else None.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching user by ID: {str(e)}")
        raise


async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Register a new user with hashed password.

    Args:
        db: Database session
        user_data: User registration data

    Returns:
        Newly created User object

    Raises:
        IntegrityError: If email already exists
        Exception: For other database errors

    Example:
        >>> user_data = UserCreate(email="new@example.com", password="Pass123")
        >>> user = await register_user(db, user_data)
        >>> user.email
        'new@example.com'
    """
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(db, user_data.email)
        if existing_user:
            logger.warning("Registration attempted for an existing email")
            raise ValueError(f"Email {user_data.email} already registered")

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create new user
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info("User registered successfully")
        return new_user

    except ValueError:
        # Re-raise ValueError for duplicate email
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error during registration: {str(e)}")
        raise ValueError(f"Email {user_data.email} already registered")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error registering user: {str(e)}")
        raise


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """
    Authenticate a user with email and password.

    Args:
        db: Database session
        email: User email address
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise

    Example:
        >>> user = await authenticate_user(db, "user@example.com", "Pass123")
        >>> user.email if user else None
        'user@example.com'
    """
    try:
        # Get user by email
        user = await get_user_by_email(db, email)
        if not user:
            logger.warning("Authentication failed - user not found")
            return None

        # Check if user is active
        if not user.is_active:
            logger.warning("Authentication failed - inactive user")
            return None

        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning("Authentication failed - invalid password")
            return None

        logger.info("User authenticated successfully")
        return user

    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise


async def deactivate_user(db: AsyncSession, public_id: str) -> Optional[User]:
    """
    Deactivate a user account.

    Args:
        db: Database session
        public_id: User public UUID to deactivate

    Returns:
        Updated User object if found, None otherwise

    Example:
        >>> user = await deactivate_user(db, "2fd3c267-e366-4cfd-99f4-6be245472585")
        >>> user.is_active if user else None
        False
    """
    try:
        if isinstance(public_id, int):
            user = await get_user_by_id(db, public_id)
        else:
            user = await get_user_by_public_id(db, public_id)
        if not user:
            logger.warning("Deactivation attempted for non-existent user")
            return None

        user.is_active = False
        await db.commit()
        await db.refresh(user)

        logger.info("User deactivated")
        return user

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deactivating user: {str(e)}")
        raise


async def activate_user(db: AsyncSession, public_id: str) -> Optional[User]:
    """
    Activate a user account.

    Args:
        db: Database session
        public_id: User public UUID to activate

    Returns:
        Updated User object if found, None otherwise

    Example:
        >>> user = await activate_user(db, "2fd3c267-e366-4cfd-99f4-6be245472585")
        >>> user.is_active if user else None
        True
    """
    try:
        if isinstance(public_id, int):
            user = await get_user_by_id(db, public_id)
        else:
            user = await get_user_by_public_id(db, public_id)
        if not user:
            logger.warning("Activation attempted for non-existent user")
            return None

        user.is_active = True
        await db.commit()
        await db.refresh(user)

        logger.info("User activated")
        return user

    except Exception as e:
        await db.rollback()
        logger.error(f"Error activating user: {str(e)}")
        raise
