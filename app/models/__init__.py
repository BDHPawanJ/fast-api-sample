"""Database models."""

# Import every model so SQLAlchemy can resolve string-based relationships
# (e.g. User.cart -> "ShoppingCart") regardless of which module is imported first.
from app.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.shopping_cart import CartItem, ShoppingCart  # noqa: F401
from app.models.user import User  # noqa: F401
