"""Database session management with async support."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Create async engine
engine = create_async_engine(
    settings.db_url,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=False,  # Disabled due to aiomysql compatibility issues
    poolclass=NullPool if settings.is_testing else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session instance

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database session created")
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rollback: {str(e)}")
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


async def init_db() -> None:
    """
    Initialize database connection.

    Tests database connectivity on application startup.
    """
    try:
        async with engine.begin() as conn:
            logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise


async def close_db() -> None:
    """
    Close database connections.

    Should be called on application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise
