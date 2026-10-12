"""Authentication API routes following contract-first response standards."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.auth import create_access_token, get_current_user
from app.api.constants import APIMessages, HTTPStatusCodes
from app.api.deps import get_password_hasher, get_uow
from app.api.openapi import problem_responses
from app.api.problem import problem_response
from app.api.schemas.generated import LoginResponse, UserResource
from app.api.schemas.user import UserCreate, UserLogin
from app.api.serialization import user_resource
from app.application.idempotency import Outcome, run_idempotent
from app.application.ports import PasswordHasher, UnitOfWork
from app.application.use_cases.auth import authenticate_user, register_user
from app.domain.errors import EmailAlreadyRegistered
from app.domain.user import User
from app.infrastructure.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=HTTPStatusCodes.CREATED,
    response_model=UserResource,
    responses=problem_responses(409, 422),
    summary="Register a new user",
    description="Create a new user account with email and password",
)
async def register(
    user_data: UserCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    uow: UnitOfWork = Depends(get_uow),
    hasher: PasswordHasher = Depends(get_password_hasher),
):
    """
    Register a new user account and return the created user resource.

    Args:
        user_data: Incoming user registration payload.
        idempotency_key: Required idempotency key for retry-safe POST.
        uow: Unit of work.
        hasher: Password hasher.

    Returns:
        UserResource: Created user resource.
    """

    async def register_and_render() -> Outcome:
        new_user = await register_user(
            uow, hasher, email=user_data.email, password=user_data.password
        )
        return HTTPStatusCodes.CREATED, user_resource(new_user).model_dump(mode="json")

    try:
        result = await run_idempotent(
            uow,
            key=idempotency_key,
            operation="auth.register",
            principal_id=None,
            payload=user_data.model_dump(),
            action=register_and_render,
        )
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=HTTPStatusCodes.CONFLICT,
            detail=APIMessages.EMAIL_ALREADY_EXISTS,
        )
    return JSONResponse(status_code=result.status, content=result.body)


@router.post(
    "/login",
    status_code=HTTPStatusCodes.OK,
    response_model=LoginResponse,
    responses=problem_responses(401, 422),
    summary="User login",
    description="Authenticate user and receive JWT access token",
)
async def login(
    credentials: UserLogin,
    uow: UnitOfWork = Depends(get_uow),
    hasher: PasswordHasher = Depends(get_password_hasher),
):
    """
    Authenticate a user and return token plus user resource.

    Args:
        credentials: Login credentials containing email and password.
        uow: Unit of work.
        hasher: Password hasher.

    Returns:
        LoginResponse: JWT token payload and user resource.
    """
    user = await authenticate_user(uow, hasher, credentials.email, credentials.password)
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

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_resource(user),
    )


@router.get(
    "/me",
    status_code=HTTPStatusCodes.OK,
    response_model=UserResource,
    responses=problem_responses(401),
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
        UserResource: Current user resource.
    """
    return user_resource(current_user)
