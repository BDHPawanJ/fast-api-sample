"""Database models."""

# Import every model so SQLAlchemy can resolve string-based relationships
# (e.g. User.cart -> "ShoppingCart") regardless of which module is imported first.
from app.infrastructure.db.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.infrastructure.db.models.product import Product  # noqa: F401
from app.infrastructure.db.models.shopping_cart import (  # noqa: F401
    CartItem,
    ShoppingCart,
)
from app.infrastructure.db.models.user import User  # noqa: F401
