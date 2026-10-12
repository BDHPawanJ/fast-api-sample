"""Domain errors raised when business rules are violated."""


class DomainError(Exception):
    """Base class for all business-rule violations."""

    code = "DOMAIN_ERROR"


class NotFoundError(DomainError):
    """A referenced entity does not exist."""

    code = "NOT_FOUND"


class ProductNotFound(NotFoundError):
    """Product with the given identifier does not exist."""

    code = "PRODUCT_NOT_FOUND"


class InvalidProduct(DomainError):
    """Product attributes violate catalog invariants."""

    code = "INVALID_PRODUCT"


class EmailAlreadyRegistered(DomainError):
    """A user with this email already exists."""

    code = "EMAIL_ALREADY_REGISTERED"


class InvalidQuantity(DomainError):
    """Requested cart quantity is out of the allowed range."""

    code = "INVALID_QUANTITY"


class InsufficientStock(DomainError):
    """Requested quantity exceeds the product's available stock."""

    code = "INSUFFICIENT_STOCK"


class CartItemNotFound(NotFoundError):
    """The cart has no line for the given product."""

    code = "CART_ITEM_NOT_FOUND"
