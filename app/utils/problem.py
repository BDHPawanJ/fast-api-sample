"""Helpers for producing Problem Details error responses."""

from typing import Any, Dict, List, Optional

from fastapi.responses import JSONResponse

from app.schemas.problem import ProblemDetails


def problem_response(
    *,
    status: int,
    type_uri: str,
    title: str,
    detail: str,
    instance: str,
    code: str,
    trace_id: str,
    errors: Optional[List[Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """
    Build a Problem Details JSON response with RFC 7807 media type.

    Args:
        status: HTTP status code.
        type_uri: Stable URI identifying problem category.
        title: Short problem summary.
        detail: Context-specific explanation.
        instance: Request path/resource occurrence.
        code: Stable machine-readable application code.
        trace_id: Correlation ID for logs/traces.
        errors: Optional detailed validation/business errors.
        headers: Optional additional response headers.

    Returns:
        JSONResponse: application/problem+json response payload.
    """

    payload = ProblemDetails(
        type=type_uri,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        code=code,
        trace_id=trace_id,
        errors=errors,
    ).model_dump(exclude_none=True)

    response_headers = {"Content-Type": "application/problem+json"}
    if headers:
        response_headers.update(headers)
    return JSONResponse(status_code=status, content=payload, headers=response_headers)
