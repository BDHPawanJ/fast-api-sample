"""Serialization helpers for API resource responses."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.api.schemas.generated import ProductResource, UserResource
from app.domain.product import Product
from app.domain.user import User


def as_utc(dt: datetime) -> datetime:
    """
    Normalize datetime to timezone-aware UTC.

    Args:
        dt: Datetime value; naive values are assumed to be UTC.

    Returns:
        datetime: Timezone-aware UTC datetime.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc_z(dt: datetime) -> str:
    """
    Convert datetime to ISO-8601 UTC string with trailing Z.

    Args:
        dt: Datetime value to normalize.

    Returns:
        str: UTC ISO-8601 timestamp ending with Z.
    """
    return as_utc(dt).isoformat().replace("+00:00", "Z")


def money_from_json(value: float) -> Decimal:
    """
    Convert a JSON number price into an exact Decimal.

    Goes through ``str`` so the shortest decimal repr is used: 0.1 becomes
    Decimal("0.1"), not 0.1000000000000000055511151231257827.

    Args:
        value: Price as parsed from the request body.

    Returns:
        Decimal: Exact price.
    """
    return Decimal(str(value))


def money_to_json(value: Decimal) -> float:
    """
    Convert a Decimal price to a JSON number for responses.

    The contract types price as ``number``; values have at most 2 decimals and
    8 integer digits, so the float repr round-trips exactly.

    Args:
        value: Exact price.

    Returns:
        float: Price for the response body.
    """
    return float(value)


def user_resource(user: User) -> UserResource:
    """
    Serialize user model as API resource representation.

    Args:
        user: Domain user.

    Returns:
        UserResource: User API resource payload.
    """
    return UserResource(
        user_id=UUID(user.public_id),
        email=user.email,
        is_active=user.is_active,
        created_at=as_utc(user.created_at),
        updated_at=as_utc(user.updated_at),
    )


def product_resource(product: Product) -> ProductResource:
    """
    Serialize product model as API resource representation.

    Args:
        product: Domain product.

    Returns:
        ProductResource: Product API resource payload.
    """
    return ProductResource(
        product_id=UUID(product.public_id),
        name=product.name,
        description=product.description,
        price=money_to_json(product.price),
        stock=product.stock,
        created_at=as_utc(product.created_at),
        updated_at=as_utc(product.updated_at),
    )


def make_etag(updated_at: datetime, public_id: str) -> str:
    """
    Build deterministic ETag for mutable resources.

    Args:
        updated_at: Last updated timestamp.
        public_id: Public resource identifier.

    Returns:
        str: Strong ETag string including quotes.
    """
    return f'"{public_id}:{to_utc_z(updated_at)}"'
