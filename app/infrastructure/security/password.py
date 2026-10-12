"""Bcrypt implementation of the PasswordHasher port."""

from passlib.context import CryptContext

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

# bcrypt only uses the first 72 bytes of a password.
BCRYPT_MAX_BYTES = 72


class BcryptPasswordHasher:
    """Password hasher backed by passlib's bcrypt scheme."""

    def __init__(self) -> None:
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__truncate_error=False,  # Don't raise error, truncate automatically
        )

    def hash(self, password: str) -> str:
        """
        Hash a plain password using bcrypt.

        Passwords longer than 72 bytes are truncated on a UTF-8 character
        boundary, matching what bcrypt would verify.

        Args:
            password: Plain text password to hash.

        Returns:
            str: Bcrypt hash.

        Raises:
            ValueError: Hashing failed.
        """
        try:
            return self._context.hash(_truncate(password))
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise ValueError(f"Failed to hash password: {str(e)}")

    def verify(self, password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a bcrypt hash.

        Args:
            password: Plain text password to verify.
            hashed_password: Stored bcrypt hash.

        Returns:
            bool: True if the password matches; False otherwise or if the
            hash is malformed.
        """
        try:
            return self._context.verify(password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False


def _truncate(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) <= BCRYPT_MAX_BYTES:
        return password
    logger.debug("Password truncated to 72 bytes for bcrypt")
    # errors="ignore" drops a multi-byte character cut in half at the boundary.
    return encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")
