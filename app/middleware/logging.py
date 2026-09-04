"""Logging middleware for request/response tracking."""

import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs request details including method, path, query parameters,
    and response status with timing information.

    Attributes:
        None: Middleware behavior is defined through dispatch lifecycle.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Log request details
        start_time = time.time()

        logger.info(
            f"Request started",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                }
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log response details
            logger.info(
                f"Request completed",
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                    }
                },
            )

            raise


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking endpoint performance.

    Adds timing information to response headers.

    Attributes:
        None: Middleware behavior is defined through dispatch lifecycle.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add timing header.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with timing header
        """
        start_time = time.time()

        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration:.4f}"

        return response
