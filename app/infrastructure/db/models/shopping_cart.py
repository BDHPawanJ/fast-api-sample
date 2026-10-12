"""Shopping cart models."""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from app.infrastructure.db.models.product import Product
    from app.infrastructure.db.models.user import User


class ShoppingCart(BaseModel):
    """Shopping cart owned by exactly one user."""

    __tablename__ = "shopping_carts"

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
        doc="Public UUID identifier for API exposure",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # unique FK is what makes this 1:1
        nullable=False,
        doc="Owning user",
    )

    user: Mapped["User"] = relationship(back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CartItem(BaseModel):
    """A product line in a shopping cart."""

    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
    )

    cart_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )

    cart: Mapped["ShoppingCart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(lazy="selectin")
