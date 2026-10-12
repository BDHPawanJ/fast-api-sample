"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

from app.api.errors import register_exception_handlers
from app.api.lifespan import app_lifespan
from app.api.middleware import configure_middlewares
from app.api.openapi import build_openapi
from app.api.schemas.generated import RootInfo
from app.api.v1.router import api_v1_router
from app.infrastructure.config import settings

OPENAPI_URL = "/openapi.json"

# API docs are opt-in via DOCS_ENABLED and always off in production (see Settings).
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI service with JWT auth and product APIs.",
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    openapi_url=OPENAPI_URL if settings.DOCS_ENABLED else None,
    debug=settings.DEBUG,
    lifespan=app_lifespan,
)

configure_middlewares(app)
register_exception_handlers(app)

app.include_router(api_v1_router)
app.openapi = build_openapi(app)


if settings.DOCS_ENABLED:
    # Registered manually to pin the ReDoc bundle, so redoc_url=None does not
    # cover it; it must be gated separately.
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Serve ReDoc with a pinned stable JavaScript bundle URL."""
        return get_redoc_html(
            openapi_url=OPENAPI_URL,
            title=f"{settings.APP_NAME} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
        )


@app.get(
    "/",
    tags=["Root"],
    response_model=RootInfo,
    status_code=200,
    summary="Root endpoint",
)
async def root():
    """
    Return basic API information.

    Returns:
        RootInfo: Service metadata and documentation endpoints.
    """
    return RootInfo(
        application=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs=app.docs_url,
        redoc="/redoc" if settings.DOCS_ENABLED else None,
        environment=settings.ENVIRONMENT,
    )
