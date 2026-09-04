"""Authentication API routes following contract-first response standards."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import APIMessages, HTTPStatusCodes
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import authenticate_user, register_user
from app.services.idempotency_service import (
    decode_response_body,
    get_idempotency_record,
    request_hash,
    save_idempotency_record,
)
from app.utils.problem import problem_response
from app.utils.serialization import user_resource

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=HTTPStatusCodes.CREATED,
    response_model=dict,
    summary="Register a new user",
    description="Create a new user account with email and password",
)
async def register(
    request: Request,
    user_data: UserCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account and return the created user resource.

    Args:
        request: Incoming HTTP request.
        user_data: Incoming user registration payload.
        idempotency_key: Required idempotency key for retry-safe POST.
        db: Active database session dependency.

    Returns:
        dict: Created user resource.
    """
    payload_hash = request_hash(user_data.model_dump())
    record = await get_idempotency_record(
        db,
        key=idempotency_key,
        operation="auth.register",
        principal_id=None,
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

    try:
        new_user = await register_user(db, user_data)
        body = user_resource(new_user)
        await save_idempotency_record(
            db,
            key=idempotency_key,
            operation="auth.register",
            principal_id=None,
            request_body_hash=payload_hash,
            response_status=HTTPStatusCodes.CREATED,
            response_body=body,
        )
        return JSONResponse(status_code=HTTPStatusCodes.CREATED, content=body)
    except ValueError:
        raise HTTPException(
            status_code=HTTPStatusCodes.CONFLICT,
            detail=APIMessages.EMAIL_ALREADY_EXISTS,
        )


@router.post(
    "/login",
    status_code=HTTPStatusCodes.OK,
    response_model=dict,
    summary="User login",
    description="Authenticate user and receive JWT access token",
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return token plus user resource.

    Args:
        credentials: Login credentials containing email and password.
        db: Active database session dependency.

    Returns:
        dict: JWT token payload and user resource.
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=HTTPStatusCodes.UNAUTHORIZED,
            detail=APIMessages.INVALID_CREDENTIALS,
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.public_id},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_resource(user),
    }


@router.get(
    "/me",
    status_code=HTTPStatusCodes.OK,
    response_model=dict,
    summary="Get current user",
    description="Get currently authenticated user information",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve information about the authenticated user.

    Args:
        current_user: Authenticated user resolved by dependency injection.

    Returns:
        dict: Current user resource.
    """
    return user_resource(current_user)
