"""Pydantic schemas for product CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProductBase(BaseModel):
    """
    Base product schema with common fields.

    Attributes:
        name: Product name
        description: Product description (optional)
        price: Product price (must be positive)
        stock: Available stock quantity (non-negative)
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Product name",
        examples=["Laptop", "Smartphone", "Headphones"],
    )

    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed product description",
        examples=["High-performance laptop with 16GB RAM and 512GB SSD"],
    )

    price: float = Field(
        ...,
        gt=0,
        description="Product price (must be positive)",
        examples=[999.99, 599.50, 149.99],
    )

    stock: int = Field(
        ...,
        ge=0,
        description="Available stock quantity (non-negative)",
        examples=[100, 50, 0],
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """
        Validate price is positive and has at most 2 decimal places.

        Args:
            v: Price value

        Returns:
            Validated price rounded to 2 decimal places

        Raises:
            ValueError: If price is invalid
        """
        if v <= 0:
            raise ValueError("Price must be greater than 0")

        # Round to 2 decimal places
        return round(v, 2)

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, v: int) -> int:
        """
        Validate stock is non-negative.

        Args:
            v: Stock value

        Returns:
            Validated stock value

        Raises:
            ValueError: If stock is negative
        """
        if v < 0:
            raise ValueError("Stock cannot be negative")
        return v


class ProductCreate(ProductBase):
    """
    Schema for creating a new product.

    Inherits all fields from ProductBase.
    """

    class Config:
        """
        Pydantic model configuration for ProductCreate schema.

        Attributes:
            json_schema_extra: Example payload for OpenAPI docs.
        """

        json_schema_extra = {
            "example": {
                "name": "Laptop",
                "description": "High-performance laptop with 16GB RAM and 512GB SSD",
                "price": 999.99,
                "stock": 50,
            }
        }


class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product.

    All fields are optional to allow partial updates.

    Attributes:
        name: Product name (optional)
        description: Product description (optional)
        price: Product price (optional, must be positive)
        stock: Available stock quantity (optional, non-negative)
    """

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Product name",
        examples=["Updated Laptop"],
    )

    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed product description",
        examples=["Updated description with new features"],
    )

    price: Optional[float] = Field(
        None,
        gt=0,
        description="Product price (must be positive)",
        examples=[899.99],
    )

    stock: Optional[int] = Field(
        None,
        ge=0,
        description="Available stock quantity (non-negative)",
        examples=[75],
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate and normalize price when present in update payload.

        Args:
            v: Optional price value.

        Returns:
            Optional[float]: Rounded price when provided, otherwise None.

        Raises:
            ValueError: If provided price is not greater than zero.
        """
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be greater than 0")
            return round(v, 2)
        return v

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate stock value when present in update payload.

        Args:
            v: Optional stock value.

        Returns:
            Optional[int]: Stock value when valid, otherwise None.

        Raises:
            ValueError: If provided stock value is negative.
        """
        if v is not None and v < 0:
            raise ValueError("Stock cannot be negative")
        return v

    class Config:
        """
        Pydantic model configuration for ProductUpdate schema.

        Attributes:
            json_schema_extra: Example payload for OpenAPI docs.
        """

        json_schema_extra = {
            "example": {
                "name": "Updated Laptop",
                "price": 899.99,
                "stock": 75,
            }
        }


class ProductResponse(ProductBase):
    """
    Schema for product data in responses.

    Includes all base fields plus ID and timestamps.

    Attributes:
        id: Product ID
        name: Product name
        description: Product description
        price: Product price
        stock: Available stock quantity
        created_at: Product creation timestamp
        updated_at: Last update timestamp
    """

    id: int = Field(..., description="Product ID")
    created_at: datetime = Field(..., description="Product creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """
        Pydantic model configuration for ProductResponse schema.

        Attributes:
            from_attributes: Enables ORM object parsing.
            json_schema_extra: Example payload for OpenAPI docs.
        """

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Laptop",
                "description": "High-performance laptop with 16GB RAM and 512GB SSD",
                "price": 999.99,
                "stock": 50,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00",
            }
        }
