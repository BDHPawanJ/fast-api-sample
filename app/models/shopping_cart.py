"""Shopping cart models."""

from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ShoppingCart(BaseModel):
    """Shopping cart owned by exactly one user."""

    __tablename__ = "shopping_carts"

    public_id = Column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
        doc="Public UUID identifier for API exposure",
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # unique FK is what makes this 1:1
        nullable=False,
        doc="Owning user",
    )

    user = relationship("User", back_populates="cart")
    items = relationship(
        "CartItem",
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

    cart_id = Column(
        Integer,
        ForeignKey("shopping_carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity = Column(Integer, nullable=False, default=1, server_default=text("1"))

    cart = relationship("ShoppingCart", back_populates="items")
    product = relationship("Product", lazy="selectin")
