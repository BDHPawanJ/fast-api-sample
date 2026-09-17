"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

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
    redoc_url=None,
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
    lifespan=app_lifespan,
)

configure_middlewares(app)
register_exception_handlers(app)

app.include_router(api_v1_router)


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Serve ReDoc with a pinned stable JavaScript bundle URL."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
    )


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
