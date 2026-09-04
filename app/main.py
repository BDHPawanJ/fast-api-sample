"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.handlers.errors import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.lifespan import app_lifespan
from app.core.middleware import configure_middlewares

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI service with JWT auth and product APIs.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
    lifespan=app_lifespan,
)

configure_middlewares(app)
register_exception_handlers(app)

app.include_router(api_v1_router)


@app.get(
    "/", tags=["Root"], response_model=dict, status_code=200, summary="Root endpoint"
)
async def root():
    """
    Return basic API information.

    Returns:
        dict: Service metadata and documentation endpoints.
    """
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "environment": settings.ENVIRONMENT,
    }
