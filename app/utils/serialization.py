"""Serialization helpers for API resource responses."""

from datetime import datetime, timezone
from typing import Optional

from app.models.product import Product
from app.models.user import User


def to_utc_z(dt: datetime) -> str:
    """
    Convert datetime to ISO-8601 UTC string with trailing Z.

    Args:
        dt: Datetime value to normalize.

    Returns:
        str: UTC ISO-8601 timestamp ending with Z.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def user_resource(user: User) -> dict:
    """
    Serialize user model as API resource representation.

    Args:
        user: User model instance.

    Returns:
        dict: User API resource payload.
    """
    return {
        "user_id": user.public_id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": to_utc_z(user.created_at),
        "updated_at": to_utc_z(user.updated_at),
    }


def product_resource(product: Product) -> dict:
    """
    Serialize product model as API resource representation.

    Args:
        product: Product model instance.

    Returns:
        dict: Product API resource payload.
    """
    return {
        "product_id": product.public_id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "created_at": to_utc_z(product.created_at),
        "updated_at": to_utc_z(product.updated_at),
    }


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
