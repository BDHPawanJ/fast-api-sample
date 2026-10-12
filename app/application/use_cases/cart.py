"""Shopping cart use cases.

Cart writes are read-modify-write. If a concurrent request creates the same
cart or line first, the repository raises ``ConcurrencyConflict`` and the use
case re-runs in a fresh transaction, re-applying the change to the cart as the
other request left it. These use cases must therefore run as the outermost
unit of work: a retry inside someone else's transaction would reuse a
transaction that has already been marked for rollback.
"""

import logging
from typing import Awaitable, Callable

from app.application.errors import ConcurrencyConflict
from app.application.ports import UnitOfWork
from app.domain.cart import Cart
from app.domain.errors import ProductNotFound
from app.domain.product import Product

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


async def get_cart(uow: UnitOfWork, user_id: int) -> Cart:
    """
    Return the user's cart, or an empty unsaved cart if they have none.

    Args:
        uow: Unit of work.
        user_id: Internal ID of the cart owner.

    Returns:
        Cart: The user's cart.
    """
    async with uow:
        return await uow.carts.get_for_user(user_id) or Cart(user_id=user_id)


async def add_to_cart(
    uow: UnitOfWork, user_id: int, product_id: str, quantity: int = 1
) -> Cart:
    """
    Add a product to the user's cart, creating the cart if needed.

    Args:
        uow: Unit of work.
        user_id: Internal ID of the cart owner.
        product_id: Product public UUID.
        quantity: Quantity to add on top of what is already in the cart.

    Returns:
        Cart: Updated cart.

    Raises:
        ProductNotFound: The product does not exist.
        InvalidQuantity: Quantity is out of range.
        InsufficientStock: Not enough stock for the resulting quantity.
        ConcurrencyConflict: Still conflicting after ``MAX_ATTEMPTS``.
    """

    async def add(cart: Cart) -> None:
        cart.add_item(await _require_product(uow, product_id), quantity)

    cart = await _change_cart(uow, user_id, add)
    logger.info("Product added to cart")
    return cart


async def update_cart_item(
    uow: UnitOfWork, user_id: int, product_id: str, quantity: int
) -> Cart:
    """
    Set the quantity of a product in the user's cart; 0 removes it.

    Args:
        uow: Unit of work.
        user_id: Internal ID of the cart owner.
        product_id: Product public UUID.
        quantity: New quantity for the line.

    Returns:
        Cart: Updated cart.

    Raises:
        ProductNotFound: The product does not exist.
        CartItemNotFound: Removing a product that is not in the cart.
        InvalidQuantity: Quantity is out of range.
        InsufficientStock: Not enough stock for the quantity.
        ConcurrencyConflict: Still conflicting after ``MAX_ATTEMPTS``.
    """

    async def set_quantity(cart: Cart) -> None:
        cart.set_quantity(await _require_product(uow, product_id), quantity)

    return await _change_cart(uow, user_id, set_quantity)


async def remove_from_cart(uow: UnitOfWork, user_id: int, product_id: str) -> Cart:
    """
    Remove a product from the user's cart.

    Args:
        uow: Unit of work.
        user_id: Internal ID of the cart owner.
        product_id: Product public UUID.

    Returns:
        Cart: Updated cart.

    Raises:
        ProductNotFound: The product does not exist.
        CartItemNotFound: The product is not in the cart.
    """
    return await update_cart_item(uow, user_id, product_id, 0)


async def clear_cart(uow: UnitOfWork, user_id: int) -> Cart:
    """
    Remove every line from the user's cart.

    Args:
        uow: Unit of work.
        user_id: Internal ID of the cart owner.

    Returns:
        Cart: The emptied cart.
    """
    async with uow:
        cart = await uow.carts.get_for_user(user_id)
        if cart is None:
            return Cart(user_id=user_id)
        cart.clear()
        await uow.carts.save(cart)
        await uow.commit()

    return cart


async def _change_cart(
    uow: UnitOfWork, user_id: int, change: Callable[[Cart], Awaitable[None]]
) -> Cart:
    """Load (or start) the user's cart, apply ``change``, save; retry on conflict."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with uow:
                cart = await uow.carts.get_for_user(user_id) or Cart(user_id=user_id)
                await change(cart)
                await uow.carts.save(cart)
                await uow.commit()
            return cart
        except ConcurrencyConflict:
            if attempt == MAX_ATTEMPTS:
                raise
            logger.info(f"Cart write conflicted, retrying (attempt {attempt})")
    raise AssertionError("unreachable")


async def _require_product(uow: UnitOfWork, product_id: str) -> Product:
    product = await uow.products.get_by_public_id(product_id)
    if product is None:
        raise ProductNotFound(f"Product {product_id} not found")
    return product
