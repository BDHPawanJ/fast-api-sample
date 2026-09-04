"""Application lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import close_db, init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manage startup and shutdown lifecycle for the API application.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control is returned to FastAPI after startup.
    """
    logger.info("Starting up application...")
    try:
        await init_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    yield

    logger.info("Shutting down application...")
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
