"""Product use cases.


Page sizes are an API policy: callers pass an explicit, already-validated
``limit``.
"""

import logging
from decimal import Decimal
from typing import Any, Mapping, Optional

from app.application.ports import UnitOfWork
from app.domain.product import Product

logger = logging.getLogger(__name__)


async def create_product(
    uow: UnitOfWork,
    *,
    name: str,
    price: Decimal,
    stock: int = 0,
    description: Optional[str] = None,
) -> Product:
    """
    Create a new product.

    Args:
        uow: Unit of work.
        name: Product name.
        price: Unit price in whole cents; must be positive.
        stock: Initial stock; must not be negative.
        description: Optional description.

    Returns:
        Product: Newly created product with id and timestamps assigned.
    """
    async with uow:
        product = Product(name=name, description=description, price=price, stock=stock)
        await uow.products.add(product)
        await uow.commit()

    logger.info(f"Product created successfully: {product.name} (ID: {product.id})")
    return product


async def get_product_by_id(uow: UnitOfWork, product_id: int) -> Optional[Product]:
    """
    Retrieve a product by internal ID.

    Args:
        uow: Unit of work.
        product_id: Internal product ID.

    Returns:
        Optional[Product]: Product if found, else None.
    """
    async with uow:
        return await uow.products.get(product_id)


async def get_product_by_public_id(
    uow: UnitOfWork, product_id: str
) -> Optional[Product]:
    """
    Retrieve a product by public UUID identifier.

    Args:
        uow: Unit of work.
        product_id: Product public UUID.

    Returns:
        Optional[Product]: Product if found, else None.
    """
    async with uow:
        return await uow.products.get_by_public_id(product_id)


async def get_products_by_cursor(
    uow: UnitOfWork,
    *,
    limit: int,
    cursor_last_id: Optional[int] = None,
    search: Optional[str] = None,
) -> list[Product]:
    """
    Retrieve products using cursor-based pagination.

    Args:
        uow: Unit of work.
        limit: Max number of items to return.
        cursor_last_id: Internal ID after which records should be fetched.
        search: Optional search text on name/description.

    Returns:
        list[Product]: Products ordered by id for the current cursor page.
    """
    async with uow:
        return await uow.products.list_after(
            limit=limit, after_id=cursor_last_id, search=search
        )


async def get_all_products(
    uow: UnitOfWork, *, limit: int, skip: int = 0
) -> tuple[list[Product], int]:
    """
    Retrieve products newest first with offset pagination.

    Args:
        uow: Unit of work.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        tuple[list[Product], int]: Page of products and total count.
    """
    async with uow:
        return await uow.products.list_newest(offset=skip, limit=limit)


async def search_products(
    uow: UnitOfWork, query: str, *, limit: int, skip: int = 0
) -> tuple[list[Product], int]:
    """
    Search products by name or description.

    Args:
        uow: Unit of work.
        query: Search text.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        tuple[list[Product], int]: Page of matching products and total count.
    """
    async with uow:
        return await uow.products.list_newest(offset=skip, limit=limit, search=query)


async def get_low_stock_products(
    uow: UnitOfWork,
    *,
    limit: int,
    threshold: int = Product.LOW_STOCK_THRESHOLD,
    skip: int = 0,
) -> tuple[list[Product], int]:
    """
    Get products with 0 < stock <= threshold, lowest stock first.

    Args:
        uow: Unit of work.
        threshold: Stock level threshold.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        tuple[list[Product], int]: Page of low stock products and total count.
    """
    async with uow:
        return await uow.products.list_low_stock(
            threshold=threshold, offset=skip, limit=limit
        )


async def get_out_of_stock_products(
    uow: UnitOfWork, *, limit: int, skip: int = 0
) -> tuple[list[Product], int]:
    """
    Get products with no stock, most recently updated first.

    Args:
        uow: Unit of work.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        tuple[list[Product], int]: Page of out of stock products and total count.
    """
    async with uow:
        return await uow.products.list_out_of_stock(offset=skip, limit=limit)


async def update_product(
    uow: UnitOfWork, product_id: str, changes: Mapping[str, Any]
) -> Optional[Product]:
    """
    Partially update an existing product.

    Args:
        uow: Unit of work.
        product_id: Product public UUID.
        changes: Fields to change; omitted fields are left untouched.

    Returns:
        Optional[Product]: Updated product, or None if it does not exist.

    Raises:
        InvalidProduct: The update would break product invariants.
    """
    async with uow:
        product = await uow.products.get_by_public_id(product_id)
        if product is None:
            logger.warning("Update attempted for non-existent product")
            return None

        product.update_details(**changes)
        await uow.products.save(product)
        await uow.commit()

    logger.info("Product updated successfully")
    return product


async def delete_product(uow: UnitOfWork, product_id: str) -> bool:
    """
    Delete a product (hard delete).

    Args:
        uow: Unit of work.
        product_id: Product public UUID.

    Returns:
        bool: True if deleted, False if it did not exist.
    """
    async with uow:
        product = await uow.products.get_by_public_id(product_id)
        if product is None:
            logger.warning("Delete attempted for non-existent product")
            return False

        await uow.products.delete(product)
        await uow.commit()

    logger.info("Product deleted successfully")
    return True
