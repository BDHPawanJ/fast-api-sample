"""Middleware registration helpers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.logging import RequestLoggingMiddleware, TimingMiddleware


def configure_middlewares(app: FastAPI) -> None:
    """
    Register all application middleware in one place.

    Args:
        app: FastAPI application instance.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=(
            settings.CORS_ALLOW_METHODS.split(",")
            if isinstance(settings.CORS_ALLOW_METHODS, str)
            else ["*"]
        ),
        allow_headers=(
            settings.CORS_ALLOW_HEADERS.split(",")
            if isinstance(settings.CORS_ALLOW_HEADERS, str)
            else ["*"]
        ),
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TimingMiddleware)
