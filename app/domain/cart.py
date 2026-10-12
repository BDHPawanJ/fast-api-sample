"""Shopping cart aggregate."""

from dataclasses import dataclass, field
from typing import ClassVar
from uuid import uuid4

from app.domain.errors import (
    CartItemNotFound,
    InsufficientStock,
    InvalidQuantity,
)
from app.domain.product import Product


@dataclass(eq=False)
class CartItem:
    """A product line in a cart, referencing the product's internal id."""

    product_id: int
    quantity: int


@dataclass(eq=False)
class Cart:
    """
    Shopping cart owned by exactly one user.

    All changes to cart lines go through this aggregate so quantity and stock
    rules are enforced in one place.
    """

    user_id: int
    items: list[CartItem] = field(default_factory=list)
    public_id: str = field(default_factory=lambda: str(uuid4()))
    id: int | None = None

    MAX_QUANTITY_PER_LINE: ClassVar[int] = 99

    def add_item(self, product: Product, quantity: int = 1) -> None:
        """
        Add ``quantity`` of a product, merging with an existing line.

        Raises:
            InvalidQuantity: quantity < 1 or the line would exceed the limit.
            InsufficientStock: the resulting quantity exceeds product stock.
        """
        if quantity < 1:
            raise InvalidQuantity("Quantity must be at least 1")
        self._set(product, self.quantity_of(product.id) + quantity)

    def set_quantity(self, product: Product, quantity: int) -> None:
        """
        Replace the quantity of a product line; 0 removes the line.

        Raises:
            InvalidQuantity: quantity < 0 or above the per-line limit.
            InsufficientStock: quantity exceeds product stock.
            CartItemNotFound: quantity is 0 and the product is not in the cart.
        """
        if quantity < 0:
            raise InvalidQuantity("Quantity cannot be negative")
        if quantity == 0:
            self.remove_item(_product_id(product))
            return
        self._set(product, quantity)

    def remove_item(self, product_id: int) -> None:
        """
        Remove a product line.

        Raises:
            CartItemNotFound: the product is not in the cart.
        """
        line = self._line(product_id)
        if line is None:
            raise CartItemNotFound(f"Product {product_id} is not in the cart")
        self.items.remove(line)

    def clear(self) -> None:
        """Remove every line."""
        self.items.clear()

    def quantity_of(self, product_id: int | None) -> int:
        """Quantity of a product currently in the cart (0 if absent)."""
        line = self._line(product_id)
        return line.quantity if line else 0

    @property
    def total_quantity(self) -> int:
        """Sum of quantities across all lines."""
        return sum(item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        """Whether the cart has no lines."""
        return not self.items

    def _set(self, product: Product, quantity: int) -> None:
        product_id = _product_id(product)
        if quantity > self.MAX_QUANTITY_PER_LINE:
            raise InvalidQuantity(
                f"Quantity cannot exceed {self.MAX_QUANTITY_PER_LINE} per product"
            )
        if quantity > product.stock:
            raise InsufficientStock(
                f"Requested {quantity} of {product.public_id}, "
                f"only {product.stock} available"
            )

        line = self._line(product_id)
        if line:
            line.quantity = quantity
        else:
            self.items.append(CartItem(product_id=product_id, quantity=quantity))

    def _line(self, product_id: int | None) -> CartItem | None:
        return next((i for i in self.items if i.product_id == product_id), None)


def _product_id(product: Product) -> int:
    if product.id is None:
        raise ValueError("Product must be persisted before adding to a cart")
    return product.id
