"""Authentication use cases: registration, login, account status."""

import logging
from typing import Optional

from app.application.ports import PasswordHasher, UnitOfWork
from app.domain.errors import EmailAlreadyRegistered
from app.domain.user import User

logger = logging.getLogger(__name__)


async def get_user_by_email(uow: UnitOfWork, email: str) -> Optional[User]:
    """
    Retrieve a user by email address.

    Args:
        uow: Unit of work.
        email: User email address.

    Returns:
        Optional[User]: User if found, else None.
    """
    async with uow:
        return await uow.users.get_by_email(email)


async def get_user_by_public_id(uow: UnitOfWork, public_id: str) -> Optional[User]:
    """
    Retrieve a user by public UUID.

    Args:
        uow: Unit of work.
        public_id: User public UUID identifier.

    Returns:
        Optional[User]: User if found, else None.
    """
    async with uow:
        return await uow.users.get_by_public_id(public_id)


async def get_user_by_id(uow: UnitOfWork, user_id: int) -> Optional[User]:
    """
    Retrieve a user by internal numeric identifier.

    Args:
        uow: Unit of work.
        user_id: Internal user ID.

    Returns:
        Optional[User]: User if found, else None.
    """
    async with uow:
        return await uow.users.get(user_id)


async def register_user(
    uow: UnitOfWork, hasher: PasswordHasher, *, email: str, password: str
) -> User:
    """
    Register a new user with a hashed password.

    Args:
        uow: Unit of work.
        hasher: Password hasher.
        email: Email address; must not be registered yet.
        password: Plain text password.

    Returns:
        User: Newly created user.

    Raises:
        EmailAlreadyRegistered: The email is already taken.
    """
    async with uow:
        if await uow.users.get_by_email(email):
            logger.warning("Registration attempted for an existing email")
            raise EmailAlreadyRegistered(f"Email {email} already registered")

        user = User(email=email, hashed_password=hasher.hash(password))
        await uow.users.add(user)
        await uow.commit()

    logger.info("User registered successfully")
    return user


async def authenticate_user(
    uow: UnitOfWork, hasher: PasswordHasher, email: str, password: str
) -> Optional[User]:
    """
    Authenticate a user with email and password.

    Args:
        uow: Unit of work.
        hasher: Password hasher.
        email: User email address.
        password: Plain text password.

    Returns:
        Optional[User]: User if credentials are valid and active, else None.
    """
    user = await get_user_by_email(uow, email)
    if not user:
        logger.warning("Authentication failed - user not found")
        return None

    if not user.is_active:
        logger.warning("Authentication failed - inactive user")
        return None

    if not hasher.verify(password, user.hashed_password):
        logger.warning("Authentication failed - invalid password")
        return None

    logger.info("User authenticated successfully")
    return user


async def deactivate_user(uow: UnitOfWork, public_id: str) -> Optional[User]:
    """
    Deactivate a user account.

    Args:
        uow: Unit of work.
        public_id: User public UUID.

    Returns:
        Optional[User]: Updated user, or None if it does not exist.
    """
    async with uow:
        user = await uow.users.get_by_public_id(public_id)
        if not user:
            logger.warning("Deactivation attempted for non-existent user")
            return None

        user.deactivate()
        await uow.users.save(user)
        await uow.commit()

    logger.info("User deactivated")
    return user


async def activate_user(uow: UnitOfWork, public_id: str) -> Optional[User]:
    """
    Activate a user account.

    Args:
        uow: Unit of work.
        public_id: User public UUID.

    Returns:
        Optional[User]: Updated user, or None if it does not exist.
    """
    async with uow:
        user = await uow.users.get_by_public_id(public_id)
        if not user:
            logger.warning("Activation attempted for non-existent user")
            return None

        user.activate()
        await uow.users.save(user)
        await uow.commit()

    logger.info("User activated")
    return user
