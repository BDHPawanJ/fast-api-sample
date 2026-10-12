"""SQLAlchemy-backed shopping cart repository."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.errors import ConcurrencyConflict
from app.domain.cart import Cart, CartItem
from app.infrastructure.db.models.shopping_cart import CartItem as CartItemRow
from app.infrastructure.db.models.shopping_cart import ShoppingCart as CartRow


def to_domain(row: CartRow) -> Cart:
    """Build a domain cart from an ORM row and its loaded items."""
    return Cart(
        id=row.id,
        public_id=row.public_id,
        user_id=row.user_id,
        items=[
            CartItem(product_id=item.product_id, quantity=item.quantity)
            for item in sorted(row.items, key=lambda item: item.id)
        ],
    )


class SqlAlchemyCartRepository:
    """Cart repository backed by an AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_user(self, user_id: int) -> Cart | None:
        row = await self._row_for_user(user_id)
        return to_domain(row) if row else None

    async def save(self, cart: Cart) -> None:
        # Decide insert vs update from the aggregate, never from a fresh lookup:
        # a cart built from a read that found nothing must INSERT (and lose to a
        # concurrent creator via uq user_id), not overwrite that creator's lines.
        if cart.id is None:
            row = CartRow(public_id=cart.public_id, user_id=cart.user_id, items=[])
            self.session.add(row)
        else:
            row = await self.session.scalar(
                select(CartRow).where(CartRow.id == cart.id)
            )
            if row is None:
                raise LookupError(f"Cart {cart.public_id} is not persisted")

        # Domain objects are detached snapshots, so diff them against the
        # stored lines; delete-orphan removes lines dropped from row.items.
        stored = {item.product_id: item for item in row.items}
        wanted = {item.product_id: item for item in cart.items}
        for product_id, item in wanted.items():
            if product_id in stored:
                stored[product_id].quantity = item.quantity
            else:
                row.items.append(
                    CartItemRow(product_id=product_id, quantity=item.quantity)
                )
        for product_id, item_row in stored.items():
            if product_id not in wanted:
                row.items.remove(item_row)

        try:
            await self.session.flush()
        except IntegrityError as e:
            # uq user_id / uq (cart_id, product_id): another transaction created
            # the cart or the line between our read and this write.
            raise ConcurrencyConflict(
                f"Cart for user {cart.user_id} was modified concurrently"
            ) from e
        cart.id = row.id
        cart.public_id = row.public_id

    async def _row_for_user(self, user_id: int) -> CartRow | None:
        return await self.session.scalar(
            select(CartRow).where(CartRow.user_id == user_id)
        )
