"""Product API routes aligned with API engineering standards."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from app.api.auth import get_current_user
from app.api.constants import APIMessages, HTTPStatusCodes
from app.api.deps import get_uow
from app.api.openapi import problem_responses
from app.api.pagination import decode_cursor, encode_cursor
from app.api.problem import problem_response
from app.api.schemas.generated import ProductPage, ProductResource
from app.api.schemas.product import ProductCreate, ProductUpdate
from app.api.serialization import make_etag, product_resource
from app.application.idempotency import Outcome, run_idempotent
from app.application.ports import UnitOfWork
from app.application.products import (
    create_product,
    delete_product,
    get_product_by_public_id,
    get_products_by_cursor,
    update_product,
)
from app.domain.user import User
from app.infrastructure.config import settings

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    status_code=HTTPStatusCodes.CREATED,
    response_model=ProductResource,
    responses=problem_responses(401, 409, 422),
    summary="Create a new product",
    description="Create a new product (requires authentication)",
)
async def create_new_product(
    product_data: ProductCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Create a new product.

    Args:
        product_data: Product creation payload.
        idempotency_key: Required idempotency key for retry-safe POST.
        current_user: Current authenticated user.
        uow: Unit of work.

    Returns:
        ProductResource: Created product resource.
    """

    async def create_and_render() -> Outcome:
        new_product = await create_product(uow, **product_data.to_create_args())
        return HTTPStatusCodes.CREATED, product_resource(new_product).model_dump(
            mode="json"
        )

    result = await run_idempotent(
        uow,
        key=idempotency_key,
        operation="products.create",
        principal_id=current_user.public_id,
        payload=product_data.model_dump(),
        action=create_and_render,
    )
    return JSONResponse(status_code=result.status, content=result.body)


@router.get(
    "",
    status_code=HTTPStatusCodes.OK,
    response_model=ProductPage,
    responses=problem_responses(400, 422),
    summary="List products",
    description="Get cursor-paginated list of products",
)
async def list_products(
    limit: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Maximum number of records to return",
    ),
    cursor: Optional[str] = Query(None, description="Opaque cursor token"),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Search query for product name or description",
    ),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Retrieve products using cursor pagination.

    Args:
        limit: Page size.
        cursor: Opaque cursor token.
        search: Optional search query.
        uow: Unit of work.

    Returns:
        ProductPage: Cursor pagination envelope with items and next cursor.
    """
    last_seen_id = None
    if cursor:
        last_seen_id = decode_cursor(cursor)
        if last_seen_id is None:
            raise HTTPException(
                status_code=HTTPStatusCodes.BAD_REQUEST,
                detail="Invalid cursor token",
            )

    rows = await get_products_by_cursor(
        uow,
        limit=limit + 1,
        cursor_last_id=last_seen_id,
        search=search,
    )
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    last_id = visible_rows[-1].id if has_more and visible_rows else None
    next_cursor = encode_cursor(last_id) if last_id is not None else None

    return ProductPage(
        items=[product_resource(row) for row in visible_rows],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/{product_id}",
    status_code=HTTPStatusCodes.OK,
    response_model=ProductResource,
    responses=problem_responses(404, 422),
    summary="Get product by ID",
    description="Get a single product by its UUID identifier",
)
async def get_product(
    product_id: str,
    response: Response,
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Get a single product by public UUID.

    Args:
        product_id: Product UUID identifier.
        response: Outgoing response used to set the ETag header.
        uow: Unit of work.

    Returns:
        ProductResource: Product resource representation.
    """
    product = await get_product_by_public_id(uow, product_id)
    if not product:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )

    response.headers["ETag"] = make_etag(product.updated_at, product.public_id)
    return product_resource(product)


@router.patch(
    "/{product_id}",
    status_code=HTTPStatusCodes.OK,
    response_model=ProductResource,
    responses=problem_responses(401, 404, 412, 422),
    summary="Patch product",
    description="Partially update an existing product (requires authentication)",
)
async def update_existing_product(
    request: Request,
    response: Response,
    product_id: str,
    product_data: ProductUpdate,
    if_match: str = Header(..., alias="If-Match"),
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Partially update an existing product using optimistic concurrency.

    Args:
        request: Incoming HTTP request.
        response: Outgoing response used to set the ETag header.
        product_id: Product UUID identifier.
        product_data: Product update payload.
        if_match: Expected entity tag from latest resource retrieval.
        current_user: Current authenticated user.
        uow: Unit of work.

    Returns:
        ProductResource: Updated product resource.
    """
    existing = await get_product_by_public_id(uow, product_id)
    if not existing:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )

    current_etag = make_etag(existing.updated_at, existing.public_id)
    if if_match != current_etag:
        return problem_response(
            status=412,
            type_uri="https://api.fastapi-sample.local/problems/precondition-failed",
            title="Precondition failed",
            detail="Resource state changed. Retrieve latest ETag and retry.",
            instance=request.url.path,
            code="ETAG_PRECONDITION_FAILED",
            trace_id=getattr(request.state, "request_id", "n/a"),
        )

    updated_product = await update_product(uow, product_id, product_data.to_changes())
    if not updated_product:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )

    response.headers["ETag"] = make_etag(
        updated_product.updated_at, updated_product.public_id
    )
    return product_resource(updated_product)


@router.delete(
    "/{product_id}",
    status_code=HTTPStatusCodes.NO_CONTENT,
    responses=problem_responses(401, 404, 422),
    summary="Delete product",
    description="Delete a product by UUID (requires authentication)",
)
async def delete_existing_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Delete a product by public UUID.

    Args:
        product_id: Product UUID identifier.
        current_user: Current authenticated user.
        uow: Unit of work.

    Returns:
        Response: Empty response with HTTP 204 on success.
    """
    success = await delete_product(uow, product_id)
    if not success:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )
    return Response(status_code=HTTPStatusCodes.NO_CONTENT)
