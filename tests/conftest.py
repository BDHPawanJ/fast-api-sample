"""Pytest fixtures and configuration for tests."""

import asyncio
from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.auth import create_access_token
from app.application.use_cases.auth import register_user
from app.domain.product import Product
from app.domain.user import User
from app.infrastructure.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import get_db
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.security.password import BcryptPasswordHasher
from app.main import app

# Test database URL
TEST_DATABASE_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL.replace(
    "/fastapi_sample", "/fastapi_sample_test"
)

# Create test async engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.

    Creates all tables before the test and drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client with overridden database dependency.

    Args:
        db_session: Test database session

    Yields:
        AsyncClient for making API requests
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        # httpx 0.26's ASGI app type predates Starlette's; runtime-compatible.
        transport=ASGITransport(app=app),  # pyright: ignore[reportArgumentType]
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def uow(db_session: AsyncSession) -> SqlAlchemyUnitOfWork:
    """Unit of work over the test session, for seeding data and repo tests."""
    return SqlAlchemyUnitOfWork(db_session)


@pytest.fixture
async def test_user(uow: SqlAlchemyUnitOfWork) -> User:
    """
    Create a test user in the database.

    Args:
        uow: Unit of work over the test session

    Returns:
        Created User object
    """
    return await register_user(
        uow,
        BcryptPasswordHasher(),
        email="test@example.com",
        password="TestPassword123",
    )


@pytest.fixture
async def test_token(test_user: User) -> str:
    """
    Create a JWT token for the test user.

    Args:
        test_user: Test user object

    Returns:
        JWT access token string
    """
    token = create_access_token(
        data={"sub": test_user.email, "user_id": test_user.public_id}
    )
    return token


@pytest.fixture
async def auth_headers(test_token: str) -> dict:
    """
    Create authorization headers with test token.

    Args:
        test_token: JWT access token

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
async def test_product(uow: SqlAlchemyUnitOfWork) -> Product:
    """
    Create a test product in the database.

    Args:
        uow: Unit of work over the test session

    Returns:
        Created Product object
    """
    product = Product(
        name="Test Laptop",
        description="A high-performance test laptop",
        price=Decimal("999.99"),
        stock=50,
    )
    async with uow:
        await uow.products.add(product)
        await uow.commit()
    return product


@pytest.fixture
async def test_products(uow: SqlAlchemyUnitOfWork) -> list[Product]:
    """
    Create multiple test products in the database.

    Args:
        uow: Unit of work over the test session

    Returns:
        List of created Product objects
    """
    products = [
        Product(
            name=f"Test Product {i}",
            description=f"Description for test product {i}",
            price=Decimal(100 * i),
            stock=10 * i,
        )
        for i in range(1, 6)
    ]

    async with uow:
        for product in products:
            await uow.products.add(product)
        await uow.commit()

    return products
