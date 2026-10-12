"""OpenAPI contract helpers."""

from http import HTTPStatus
from typing import Any, Callable, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas.generated import ProblemDetails

PROBLEM_MEDIA_TYPE = "application/problem+json"


def problem_responses(*status_codes: int) -> Dict[int | str, Dict[str, Any]]:
    """
    Build OpenAPI response entries documenting Problem Details errors.

    Args:
        status_codes: HTTP error status codes the operation can return.

    Returns:
        dict: Value for the route decorator's ``responses`` argument.
    """
    return {
        code: {"model": ProblemDetails, "description": HTTPStatus(code).phrase}
        for code in status_codes
    }


def build_openapi(app: FastAPI) -> Callable[[], Dict[str, Any]]:
    """
    Create an OpenAPI generator that serves errors as Problem Details.

    FastAPI documents every response model under the route's media type
    (``application/json``). Error responses are actually sent as
    ``application/problem+json``, so their content is re-keyed accordingly.

    Args:
        app: FastAPI application instance.

    Returns:
        Callable: Replacement for ``app.openapi``.
    """

    def openapi() -> Dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                for status_code, response in operation.get("responses", {}).items():
                    content = response.get("content", {})
                    if int(status_code) >= 400 and "application/json" in content:
                        content[PROBLEM_MEDIA_TYPE] = content.pop("application/json")

        app.openapi_schema = schema
        return schema

    return openapi
