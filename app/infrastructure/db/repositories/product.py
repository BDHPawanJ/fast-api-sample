"""SQLAlchemy-backed product repository."""

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.product import Product
from app.infrastructure.db.models.product import Product as ProductRow


def to_domain(row: ProductRow) -> Product:
    """Build a domain product from an ORM row."""
    return Product(
        id=row.id,
        public_id=row.public_id,
        name=row.name,
        description=row.description,
        price=row.price,
        stock=row.stock,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _copy_fields(product: Product, row: ProductRow) -> None:
    row.name = product.name
    row.description = product.description
    row.price = product.price
    row.stock = product.stock


def _search_filter(search: str):
    return or_(
        ProductRow.name.ilike(f"%{search}%"),
        ProductRow.description.ilike(f"%{search}%"),
    )


class SqlAlchemyProductRepository:
    """Product repository backed by an AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, product_id: int) -> Product | None:
        row = await self._row(ProductRow.id == product_id)
        return to_domain(row) if row else None

    async def get_by_public_id(self, public_id: str) -> Product | None:
        row = await self._row(ProductRow.public_id == public_id)
        return to_domain(row) if row else None

    async def add(self, product: Product) -> None:
        row = ProductRow(public_id=product.public_id)
        _copy_fields(product, row)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        product.id = row.id
        product.created_at = row.created_at
        product.updated_at = row.updated_at

    async def save(self, product: Product) -> None:
        row = await self._row(ProductRow.id == product.id)
        if row is None:
            raise LookupError(f"Product {product.public_id} is not persisted")
        _copy_fields(product, row)
        await self.session.flush()
        await self.session.refresh(row)
        product.updated_at = row.updated_at

    async def delete(self, product: Product) -> None:
        row = await self._row(ProductRow.id == product.id)
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    async def list_after(
        self, *, limit: int, after_id: int | None, search: str | None
    ) -> list[Product]:
        query = select(ProductRow)
        if search:
            query = query.where(_search_filter(search))
        if after_id is not None:
            query = query.where(ProductRow.id > after_id)
        query = query.order_by(ProductRow.id.asc()).limit(limit)
        return await self._list(query)

    async def list_newest(
        self, *, offset: int, limit: int, search: str | None = None
    ) -> tuple[list[Product], int]:
        criteria = [_search_filter(search)] if search else []
        return await self._page(
            criteria, ProductRow.created_at.desc(), offset=offset, limit=limit
        )

    async def list_low_stock(
        self, *, threshold: int, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        return await self._page(
            [ProductRow.stock.between(1, threshold)],
            ProductRow.stock.asc(),
            offset=offset,
            limit=limit,
        )

    async def list_out_of_stock(
        self, *, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        return await self._page(
            [ProductRow.stock == 0],
            ProductRow.updated_at.desc(),
            offset=offset,
            limit=limit,
        )

    async def _row(self, criterion) -> ProductRow | None:
        return await self.session.scalar(select(ProductRow).where(criterion))

    async def _list(self, query: Select) -> list[Product]:
        rows = (await self.session.scalars(query)).all()
        return [to_domain(row) for row in rows]

    async def _page(
        self, criteria: list, order_by, *, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        total = (
            await self.session.scalar(
                select(func.count(ProductRow.id)).where(*criteria)
            )
            or 0
        )
        items = await self._list(
            select(ProductRow)
            .where(*criteria)
            .order_by(order_by)
            .offset(offset)
            .limit(limit)
        )
        return items, total
