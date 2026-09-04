"""Pytest fixtures and configuration for tests."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.product import Product
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import register_user

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
TestSessionLocal = sessionmaker(
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

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user in the database.

    Args:
        db_session: Test database session

    Returns:
        Created User object
    """
    user_data = UserCreate(
        email="test@example.com",
        password="TestPassword123",
    )
    user = await register_user(db_session, user_data)
    return user


@pytest.fixture
async def test_token(test_user: User) -> str:
    """
    Create a JWT token for the test user.

    Args:
        test_user: Test user object

    Returns:
        JWT access token string
    """
    token = create_access_token(data={"sub": test_user.email, "user_id": test_user.id})
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
async def test_product(db_session: AsyncSession) -> Product:
    """
    Create a test product in the database.

    Args:
        db_session: Test database session

    Returns:
        Created Product object
    """
    product = Product(
        name="Test Laptop",
        description="A high-performance test laptop",
        price=999.99,
        stock=50,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_products(db_session: AsyncSession) -> list[Product]:
    """
    Create multiple test products in the database.

    Args:
        db_session: Test database session

    Returns:
        List of created Product objects
    """
    products = [
        Product(
            name=f"Test Product {i}",
            description=f"Description for test product {i}",
            price=float(100 * i),
            stock=10 * i,
        )
        for i in range(1, 6)
    ]

    for product in products:
        db_session.add(product)

    await db_session.commit()

    for product in products:
        await db_session.refresh(product)

    return products
