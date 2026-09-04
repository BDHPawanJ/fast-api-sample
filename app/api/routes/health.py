"""Health check endpoints for operational status."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import settings
from app.db.session import get_db
from app.utils.problem import problem_response

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=200, response_model=dict, summary="Basic health check")
async def health_check():
    """
    Return basic application health status.

    Returns:
        dict: Application status metadata.
    """
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": __version__,
        "environment": settings.ENVIRONMENT,
    }


@router.get(
    "/db", status_code=200, response_model=dict, summary="Database health check"
)
async def database_health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Test database connectivity and report health.

    Args:
        request: Incoming request instance.
        db: Database session.

    Returns:
        dict: Database health details.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected", "database_type": "mysql"}
    except Exception:
        return problem_response(
            status=503,
            type_uri="https://api.fastapi-sample.local/problems/dependency-unavailable",
            title="Dependency unavailable",
            detail="Database connectivity check failed.",
            instance=request.url.path,
            code="DATABASE_UNAVAILABLE",
            trace_id=getattr(request.state, "request_id", "n/a"),
        )


@router.get(
    "/detailed", status_code=200, response_model=dict, summary="Detailed health"
)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Return detailed system health information.

    Args:
        db: Database session.

    Returns:
        dict: Detailed application, database, and config health information.
    """
    db_status = "healthy"
    db_message = "connected"

    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
    except Exception:
        db_status = "unhealthy"
        db_message = "disconnected"

    return {
        "application": {
            "name": settings.APP_NAME,
            "version": __version__,
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "status": "healthy",
        },
        "database": {
            "status": db_status,
            "message": db_message,
            "type": "mysql",
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        },
        "configuration": {
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
            "cors_enabled": len(settings.CORS_ORIGINS) > 0,
            "jwt_algorithm": settings.ALGORITHM,
        },
        "status": "healthy" if db_status == "healthy" else "degraded",
    }
