"""Product service layer for business logic."""

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_product(db: AsyncSession, product_data: ProductCreate) -> Product:
    """
    Create a new product.

    Args:
        db: Database session
        product_data: Product creation data

    Returns:
        Newly created Product object

    Raises:
        Exception: For database errors

    Example:
        >>> product_data = ProductCreate(
        ...     name="Laptop",
        ...     description="High-performance laptop",
        ...     price=999.99,
        ...     stock=50
        ... )
        >>> product = await create_product(db, product_data)
        >>> product.name
        'Laptop'
    """
    try:
        new_product = Product(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            stock=product_data.stock,
        )

        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)

        logger.info(
            f"Product created successfully: {new_product.name} (ID: {new_product.id})"
        )
        return new_product

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating product: {str(e)}")
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating product {product_data.name}: {str(e)}")
        raise


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    """
    Retrieve a product by ID.

    Args:
        db: Database session
        product_id: Product ID

    Returns:
        Product object if found, None otherwise

    Example:
        >>> product = await get_product_by_id(db, 1)
        >>> product.id if product else None
        1
    """
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if product:
            logger.debug(f"Product found with ID: {product_id}")
        else:
            logger.debug(f"Product not found with ID: {product_id}")

        return product
    except Exception as e:
        logger.error(f"Error fetching product by ID {product_id}: {str(e)}")
        raise


async def get_product_by_public_id(
    db: AsyncSession, product_id: str
) -> Optional[Product]:
    """
    Retrieve a product by public UUID identifier.

    Args:
        db: Database session
        product_id: Product public UUID

    Returns:
        Optional[Product]: Product if found, else None.
    """
    try:
        result = await db.execute(
            select(Product).where(Product.public_id == product_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching product by public_id: {str(e)}")
        raise


async def get_products_by_cursor(
    db: AsyncSession,
    *,
    limit: int,
    cursor_last_id: Optional[int] = None,
    search: Optional[str] = None,
) -> list[Product]:
    """
    Retrieve products using cursor-based pagination.

    Args:
        db: Database session.
        limit: Max number of items to return.
        cursor_last_id: Internal ID after which records should be fetched.
        search: Optional search text on name/description.

    Returns:
        list[Product]: Ordered product records for the current cursor page.
    """
    query = select(Product)
    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
    if cursor_last_id is not None:
        query = query.where(Product.id > cursor_last_id)

    query = query.order_by(Product.id.asc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = None,
) -> tuple[List[Product], int]:
    """
    Retrieve all products with pagination.

    Args:
        db: Database session
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of products, total count)

    Example:
        >>> products, total = await get_all_products(db, skip=0, limit=10)
        >>> len(products) <= 10
        True
    """
    try:
        # Set default limit from config if not provided
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE

        # Ensure limit doesn't exceed max
        limit = min(limit, settings.MAX_PAGE_SIZE)

        # Get total count
        count_query = select(func.count(Product.id))
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Get products with pagination
        query = (
            select(Product)
            .offset(skip)
            .limit(limit)
            .order_by(Product.created_at.desc())
        )
        result = await db.execute(query)
        products = result.scalars().all()

        logger.debug(f"Retrieved {len(products)} products (total: {total})")
        return list(products), total

    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        raise


async def update_product(
    db: AsyncSession,
    product_id: str,
    product_data: ProductUpdate,
) -> Optional[Product]:
    """
    Update an existing product.

    Args:
        db: Database session
        product_id: Product ID to update
        product_data: Product update data (partial update supported)

    Returns:
        Updated Product object if found, None otherwise

    Example:
        >>> update_data = ProductUpdate(price=899.99, stock=75)
        >>> product = await update_product(db, 1, update_data)
        >>> product.price if product else None
        899.99
    """
    try:
        if isinstance(product_id, int):
            product = await get_product_by_id(db, product_id)
        else:
            product = await get_product_by_public_id(db, product_id)
        if not product:
            logger.warning("Update attempted for non-existent product")
            return None

        # Update only provided fields
        update_data = product_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)

        logger.info("Product updated successfully")
        return product

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating product: {str(e)}")
        raise


async def delete_product(db: AsyncSession, product_id: str) -> bool:
    """
    Delete a product by ID (hard delete).

    Args:
        db: Database session
        product_id: Product public UUID to delete

    Returns:
        True if deleted successfully, False if not found

    Example:
        >>> success = await delete_product(db, 1)
        >>> success
        True
    """
    try:
        if isinstance(product_id, int):
            product = await get_product_by_id(db, product_id)
        else:
            product = await get_product_by_public_id(db, product_id)
        if not product:
            logger.warning("Delete attempted for non-existent product")
            return False

        await db.delete(product)
        await db.commit()

        logger.info("Product deleted successfully")
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting product: {str(e)}")
        raise


async def search_products(
    db: AsyncSession,
    query: str,
    skip: int = 0,
    limit: int = None,
) -> tuple[List[Product], int]:
    """
    Search products by name or description.

    Args:
        db: Database session
        query: Search query string
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of matching products, total count)

    Example:
        >>> products, total = await search_products(db, "laptop", skip=0, limit=10)
        >>> all("laptop" in p.name.lower() or "laptop" in (p.description or "").lower() for p in products)
        True
    """
    try:
        # Set default limit from config if not provided
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE

        # Ensure limit doesn't exceed max
        limit = min(limit, settings.MAX_PAGE_SIZE)

        # Build search filter
        search_filter = or_(
            Product.name.ilike(f"%{query}%"),
            Product.description.ilike(f"%{query}%"),
        )

        # Get total count
        count_query = select(func.count(Product.id)).where(search_filter)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Get products with pagination
        search_query = (
            select(Product)
            .where(search_filter)
            .offset(skip)
            .limit(limit)
            .order_by(Product.created_at.desc())
        )
        result = await db.execute(search_query)
        products = result.scalars().all()

        logger.debug(
            f"Search query '{query}' found {len(products)} products (total: {total})"
        )
        return list(products), total

    except Exception as e:
        logger.error(f"Error searching products with query '{query}': {str(e)}")
        raise


async def get_low_stock_products(
    db: AsyncSession,
    threshold: int = 10,
    skip: int = 0,
    limit: int = None,
) -> tuple[List[Product], int]:
    """
    Get products with low stock.

    Args:
        db: Database session
        threshold: Stock level threshold (default: 10)
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of low stock products, total count)

    Example:
        >>> products, total = await get_low_stock_products(db, threshold=10)
        >>> all(0 < p.stock <= 10 for p in products)
        True
    """
    try:
        # Set default limit from config if not provided
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE

        # Ensure limit doesn't exceed max
        limit = min(limit, settings.MAX_PAGE_SIZE)

        # Build filter for low stock (0 < stock <= threshold)
        low_stock_filter = Product.stock.between(1, threshold)

        # Get total count
        count_query = select(func.count(Product.id)).where(low_stock_filter)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Get products with pagination
        query = (
            select(Product)
            .where(low_stock_filter)
            .offset(skip)
            .limit(limit)
            .order_by(Product.stock.asc())
        )
        result = await db.execute(query)
        products = result.scalars().all()

        logger.debug(f"Found {len(products)} low stock products (total: {total})")
        return list(products), total

    except Exception as e:
        logger.error(f"Error fetching low stock products: {str(e)}")
        raise


async def get_out_of_stock_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = None,
) -> tuple[List[Product], int]:
    """
    Get products that are out of stock.

    Args:
        db: Database session
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of out of stock products, total count)

    Example:
        >>> products, total = await get_out_of_stock_products(db)
        >>> all(p.stock == 0 for p in products)
        True
    """
    try:
        # Set default limit from config if not provided
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE

        # Ensure limit doesn't exceed max
        limit = min(limit, settings.MAX_PAGE_SIZE)

        # Build filter for out of stock
        out_of_stock_filter = Product.stock == 0

        # Get total count
        count_query = select(func.count(Product.id)).where(out_of_stock_filter)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Get products with pagination
        query = (
            select(Product)
            .where(out_of_stock_filter)
            .offset(skip)
            .limit(limit)
            .order_by(Product.updated_at.desc())
        )
        result = await db.execute(query)
        products = result.scalars().all()

        logger.debug(f"Found {len(products)} out of stock products (total: {total})")
        return list(products), total

    except Exception as e:
        logger.error(f"Error fetching out of stock products: {str(e)}")
        raise
