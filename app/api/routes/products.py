"""Product API routes aligned with API engineering standards."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import APIMessages, HTTPStatusCodes
from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.idempotency_service import (
    decode_response_body,
    get_idempotency_record,
    request_hash,
    save_idempotency_record,
)
from app.services.product_service import (
    create_product,
    delete_product,
    get_product_by_public_id,
    get_products_by_cursor,
    update_product,
)
from app.utils.cursor import decode_cursor, encode_cursor
from app.utils.problem import problem_response
from app.utils.serialization import make_etag, product_resource

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    status_code=HTTPStatusCodes.CREATED,
    response_model=dict,
    summary="Create a new product",
    description="Create a new product (requires authentication)",
)
async def create_new_product(
    request: Request,
    product_data: ProductCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new product.

    Args:
        request: Incoming HTTP request.
        product_data: Product creation payload.
        idempotency_key: Required idempotency key for retry-safe POST.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Created product resource.
    """
    payload_hash = request_hash(product_data.model_dump())
    record = await get_idempotency_record(
        db,
        key=idempotency_key,
        operation="products.create",
        principal_id=current_user.public_id,
    )
    if record:
        if record.request_hash != payload_hash:
            return problem_response(
                status=HTTPStatusCodes.CONFLICT,
                type_uri="https://api.fastapi-sample.local/problems/idempotency-key-reused",
                title="Idempotency key reuse conflict",
                detail="The same Idempotency-Key was reused with a different payload.",
                instance=request.url.path,
                code="IDEMPOTENCY_KEY_PAYLOAD_MISMATCH",
                trace_id=getattr(request.state, "request_id", "n/a"),
            )
        return JSONResponse(
            status_code=record.response_status,
            content=decode_response_body(record.response_body),
        )

    new_product = await create_product(db, product_data)
    body = product_resource(new_product)
    await save_idempotency_record(
        db,
        key=idempotency_key,
        operation="products.create",
        principal_id=current_user.public_id,
        request_body_hash=payload_hash,
        response_status=HTTPStatusCodes.CREATED,
        response_body=body,
    )
    return JSONResponse(status_code=HTTPStatusCodes.CREATED, content=body)


@router.get(
    "",
    status_code=HTTPStatusCodes.OK,
    response_model=dict,
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
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve products using cursor pagination.

    Args:
        limit: Page size.
        cursor: Opaque cursor token.
        search: Optional search query.
        db: Database session.

    Returns:
        dict: Cursor pagination envelope with items and next cursor.
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
        db,
        limit=limit + 1,
        cursor_last_id=last_seen_id,
        search=search,
    )
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    next_cursor = (
        encode_cursor(visible_rows[-1].id) if has_more and visible_rows else None
    )

    return {
        "items": [product_resource(row) for row in visible_rows],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.get(
    "/{product_id}",
    status_code=HTTPStatusCodes.OK,
    response_model=dict,
    summary="Get product by ID",
    description="Get a single product by its UUID identifier",
)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single product by public UUID.

    Args:
        product_id: Product UUID identifier.
        db: Database session.

    Returns:
        dict: Product resource representation.
    """
    product = await get_product_by_public_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )

    return JSONResponse(
        status_code=HTTPStatusCodes.OK,
        content=product_resource(product),
        headers={"ETag": make_etag(product.updated_at, product.public_id)},
    )


@router.patch(
    "/{product_id}",
    status_code=HTTPStatusCodes.OK,
    response_model=dict,
    summary="Patch product",
    description="Partially update an existing product (requires authentication)",
)
async def update_existing_product(
    request: Request,
    product_id: str,
    product_data: ProductUpdate,
    if_match: str = Header(..., alias="If-Match"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update an existing product using optimistic concurrency.

    Args:
        request: Incoming HTTP request.
        product_id: Product UUID identifier.
        product_data: Product update payload.
        if_match: Expected entity tag from latest resource retrieval.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Updated product resource.
    """
    existing = await get_product_by_public_id(db, product_id)
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

    updated_product = await update_product(db, product_id, product_data)
    if not updated_product:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )

    return JSONResponse(
        status_code=HTTPStatusCodes.OK,
        content=product_resource(updated_product),
        headers={
            "ETag": make_etag(updated_product.updated_at, updated_product.public_id)
        },
    )


@router.delete(
    "/{product_id}",
    status_code=HTTPStatusCodes.NO_CONTENT,
    summary="Delete product",
    description="Delete a product by UUID (requires authentication)",
)
async def delete_existing_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a product by public UUID.

    Args:
        product_id: Product UUID identifier.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        Response: Empty response with HTTP 204 on success.
    """
    success = await delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=HTTPStatusCodes.NOT_FOUND,
            detail=APIMessages.PRODUCT_NOT_FOUND,
        )
    return Response(status_code=HTTPStatusCodes.NO_CONTENT)
