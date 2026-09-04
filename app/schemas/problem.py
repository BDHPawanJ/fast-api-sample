"""Problem Details schemas (RFC 7807-compatible with extensions)."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProblemFieldError(BaseModel):
    """
    Field-level error metadata used in Problem Details extensions.

    Attributes:
        field: Name/path of the failing field.
        code: Stable machine-readable error code.
    """

    field: str = Field(..., description="Field name or path")
    code: str = Field(..., description="Machine-readable error code")


class ProblemDetails(BaseModel):
    """
    Standardized error response payload for API failures.

    Attributes:
        type: Stable URI identifying problem category.
        title: Short human-readable summary of the problem type.
        status: HTTP status code matching the response status.
        detail: Context-specific problem detail for this occurrence.
        instance: Request path or resource occurrence identifier.
        code: Stable application-specific error code.
        trace_id: Request correlation identifier.
        errors: Optional list of field-level or rule-level issues.
    """

    type: str = Field(..., description="Problem type URI")
    title: str = Field(..., description="Human-readable problem title")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Context-specific problem details")
    instance: str = Field(..., description="Problem occurrence path")
    code: str = Field(..., description="Machine-readable application error code")
    trace_id: str = Field(..., description="Request trace identifier")
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional detailed field/business-rule issues",
    )
