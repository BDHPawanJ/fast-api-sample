"""Global exception handler registration."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.constants import APIMessages, HTTPStatusCodes
from app.core.config import settings
from app.utils.logger import get_logger
from app.utils.problem import problem_response

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register framework and application-wide exception handlers.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Handle Starlette HTTP exceptions using Problem Details responses.

        Args:
            request: Incoming request.
            exc: Raised HTTP exception.

        Returns:
            JSONResponse: RFC 7807 compliant error payload.
        """
        return problem_response(
            status=exc.status_code,
            type_uri=f"https://api.fastapi-sample.local/problems/http-{exc.status_code}",
            title="HTTP error",
            detail=str(exc.detail),
            instance=request.url.path,
            code=f"HTTP_{exc.status_code}",
            trace_id=getattr(request.state, "request_id", "n/a"),
        )

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
        """
        Handle FastAPI HTTP exceptions using Problem Details responses.

        Args:
            request: Incoming request.
            exc: Raised HTTP exception.

        Returns:
            JSONResponse: RFC 7807 compliant error payload.
        """
        return problem_response(
            status=exc.status_code,
            type_uri=f"https://api.fastapi-sample.local/problems/http-{exc.status_code}",
            title="HTTP error",
            detail=str(exc.detail),
            instance=request.url.path,
            code=f"HTTP_{exc.status_code}",
            trace_id=getattr(request.state, "request_id", "n/a"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        Handle validation errors using Problem Details responses.

        Args:
            request: Incoming request.
            exc: Validation exception raised by FastAPI.

        Returns:
            JSONResponse: RFC 7807 validation error payload.
        """
        errors = [
            {
                "field": " -> ".join(str(location) for location in err["loc"]),
                "code": err["type"],
            }
            for err in exc.errors()
        ]
        return problem_response(
            status=HTTPStatusCodes.UNPROCESSABLE_ENTITY,
            type_uri="https://api.fastapi-sample.local/problems/validation-error",
            title="Validation failed",
            detail=APIMessages.VALIDATION_ERROR,
            instance=request.url.path,
            code="VALIDATION_ERROR",
            trace_id=getattr(request.state, "request_id", "n/a"),
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Handle unhandled exceptions using Problem Details responses.

        Args:
            request: Incoming request.
            exc: Unhandled exception instance.

        Returns:
            JSONResponse: RFC 7807 internal error payload.
        """
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return problem_response(
            status=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            type_uri="https://api.fastapi-sample.local/problems/internal-error",
            title="Internal server error",
            detail=APIMessages.INTERNAL_ERROR,
            instance=request.url.path,
            code="INTERNAL_ERROR",
            trace_id=getattr(request.state, "request_id", "n/a"),
            errors=(
                [{"field": "internal", "code": str(exc)}] if settings.DEBUG else None
            ),
        )
