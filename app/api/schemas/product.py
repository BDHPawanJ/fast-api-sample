"""Product request schemas: generated contract models plus custom normalization."""

from typing import Any, Optional

from pydantic import field_validator

from app.api.schemas import generated
from app.api.serialization import money_from_json


class ProductCreate(generated.ProductCreate):
    # Python does not inherit __doc__; keep the contract's schema description.
    __doc__ = generated.ProductCreate.__doc__

    @field_validator("price")
    @classmethod
    def round_price(cls, v: float) -> float:
        """
        Round price to 2 decimal places.

        Positivity is enforced by the contract (exclusiveMinimum: 0).

        Args:
            v: Price value

        Returns:
            Price rounded to 2 decimal places
        """
        return round(v, 2)

    def to_create_args(self) -> dict[str, Any]:
        """Keyword arguments for ``create_product``, with an exact Decimal price."""
        args = self.model_dump()
        args["price"] = money_from_json(args["price"])
        return args


class ProductUpdate(generated.ProductUpdate):
    # Python does not inherit __doc__; keep the contract's schema description.
    __doc__ = generated.ProductUpdate.__doc__

    @field_validator("price")
    @classmethod
    def round_price(cls, v: Optional[float]) -> Optional[float]:
        """
        Round price to 2 decimal places when present in update payload.

        Args:
            v: Optional price value.

        Returns:
            Optional[float]: Rounded price when provided, otherwise None.
        """
        return round(v, 2) if v is not None else v

    def to_changes(self) -> dict[str, Any]:
        """Fields the client sent, for ``update_product``, with a Decimal price."""
        changes = self.model_dump(exclude_unset=True)
        if changes.get("price") is not None:
            changes["price"] = money_from_json(changes["price"])
        return changes
