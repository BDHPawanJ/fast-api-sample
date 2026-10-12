"""Product entity for the catalog."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import uuid4

from app.domain.errors import InvalidProduct


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False)
class Product:
    """
    Catalog product.

    ``id`` is assigned by persistence and is None until the product has been
    added to a repository, which also replaces the timestamps with stored ones.
    """

    name: str
    price: Decimal
    stock: int = 0
    description: str | None = None
    public_id: str = field(default_factory=lambda: str(uuid4()))
    id: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    LOW_STOCK_THRESHOLD: ClassVar[int] = 10
    # Prices are whole cents and must fit the DECIMAL(10, 2) column.
    CENT: ClassVar[Decimal] = Decimal("0.01")
    MAX_PRICE: ClassVar[Decimal] = Decimal("99999999.99")
    UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"name", "description", "price", "stock"}
    )

    def __post_init__(self) -> None:
        self._validate()

    def update_details(self, **changes: Any) -> None:
        """
        Apply a partial update, keeping invariants intact.

        Args:
            **changes: Subset of name, description, price, stock.

        Raises:
            InvalidProduct: Unknown field or resulting state is invalid.
        """
        unknown = changes.keys() - self.UPDATABLE_FIELDS
        if unknown:
            raise InvalidProduct(f"Cannot update fields: {sorted(unknown)}")

        previous = {name: getattr(self, name) for name in changes}
        for name, value in changes.items():
            setattr(self, name, value)
        try:
            self._validate()
        except Exception:
            for name, value in previous.items():
                setattr(self, name, value)
            raise

    @property
    def is_in_stock(self) -> bool:
        """Whether any stock is available."""
        return self.stock > 0

    def is_low_stock(self, threshold: int = LOW_STOCK_THRESHOLD) -> bool:
        """Whether stock is between 1 and ``threshold`` inclusive."""
        return 0 < self.stock <= threshold

    def _validate(self) -> None:
        if not self.name:
            raise InvalidProduct("Product name is required")
        self._validate_price()
        if self.stock is None or self.stock < 0:
            raise InvalidProduct("Product stock cannot be negative")

    def _validate_price(self) -> None:
        price = self.price
        if price is None:
            raise InvalidProduct("Product price must be positive")
        if not isinstance(price, Decimal):
            # Floats would silently carry binary rounding error into money.
            raise TypeError(f"price must be a Decimal, got {type(price).__name__}")
        if not price.is_finite() or price <= 0:
            raise InvalidProduct("Product price must be positive")
        if price > self.MAX_PRICE:
            raise InvalidProduct(f"Product price cannot exceed {self.MAX_PRICE}")
        cents = price.quantize(self.CENT)
        if cents != price:
            raise InvalidProduct("Product price cannot have more than 2 decimal places")
        self.price = cents  # normalized, e.g. Decimal("10.5") -> Decimal("10.50")
