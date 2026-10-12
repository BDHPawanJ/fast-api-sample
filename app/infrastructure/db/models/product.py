"""Product table for the e-commerce catalog."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import BaseModel


class Product(BaseModel):
    """
    Product row. Business rules live on ``app.domain.product.Product``.

    Attributes:
        id: Primary key (inherited from BaseModel)
        name: Product name
        description: Detailed product description
        price: Product price (must be positive)
        stock: Available stock quantity (non-negative)
        created_at: Timestamp of product creation (inherited from BaseModel)
        updated_at: Timestamp of last update (inherited from BaseModel)
    """

    __tablename__ = "products"

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
        doc="Public UUID identifier for API exposure",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Product name",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed product description",
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Product price (must be positive)",
    )

    stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        doc="Available stock quantity",
    )

    def __repr__(self) -> str:
        """
        Return a concise string representation of the product instance.

        Returns:
            str: String containing product identifier and inventory details.
        """
        return f"<Product(id={self.id}, public_id={self.public_id}, name={self.name})>"
