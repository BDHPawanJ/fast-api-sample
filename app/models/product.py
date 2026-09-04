"""Product model for e-commerce catalog."""

from uuid import uuid4

from sqlalchemy import Column, Float, Integer, String, Text

from app.models.base import BaseModel


class Product(BaseModel):
    """
    Product model for storing product information.

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

    public_id = Column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
        doc="Public UUID identifier for API exposure",
    )

    name = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Product name",
    )

    description = Column(
        Text,
        nullable=True,
        doc="Detailed product description",
    )

    price = Column(
        Float,
        nullable=False,
        doc="Product price (must be positive)",
    )

    stock = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Available stock quantity",
    )

    def __repr__(self) -> str:
        """
        Return a concise string representation of the product instance.

        Returns:
            str: String containing product identifier and inventory details.
        """
        return f"<Product(id={self.id}, public_id={self.public_id}, name={self.name})>"

    @property
    def is_in_stock(self) -> bool:
        """
        Check whether the product has available inventory.

        Returns:
            bool: True when stock is greater than zero.
        """
        return self.stock > 0

    @property
    def is_low_stock(self, threshold: int = 10) -> bool:
        """
        Check whether stock is within low inventory threshold.

        Args:
            threshold: Maximum stock count considered low.

        Returns:
            bool: True when stock is between 1 and threshold inclusive.
        """
        return 0 < self.stock <= threshold
