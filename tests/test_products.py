"""Tests for product endpoints."""

import pytest
from httpx import AsyncClient

from app.models.product import Product


@pytest.mark.asyncio
class TestProductEndpoints:
    """Test product CRUD API endpoints."""

    async def test_create_product_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful product creation with authentication."""
        response = await client.post(
            "/api/products",
            json={
                "name": "New Laptop",
                "description": "A brand new laptop",
                "price": 1299.99,
                "stock": 25,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Product created successfully"
        assert data["data"]["name"] == "New Laptop"
        assert data["data"]["price"] == 1299.99
        assert data["data"]["stock"] == 25

    async def test_create_product_without_auth(self, client: AsyncClient):
        """Test product creation without authentication fails."""
        response = await client.post(
            "/api/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": 999.99,
                "stock": 10,
            },
        )

        assert response.status_code == 403

    async def test_create_product_invalid_price(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test product creation with invalid price fails."""
        response = await client.post(
            "/api/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": -100.00,
                "stock": 10,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_create_product_invalid_stock(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test product creation with negative stock fails."""
        response = await client.post(
            "/api/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": 999.99,
                "stock": -5,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_list_products_success(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test listing products without authentication."""
        response = await client.get("/api/products")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(test_products)
        assert "pagination" in data

    async def test_list_products_with_pagination(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test product listing with pagination."""
        response = await client.get("/api/products?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == len(test_products)
        assert data["pagination"]["page_size"] == 2

    async def test_list_products_with_search(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test product search functionality."""
        response = await client.get("/api/products?search=Product 1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1

    async def test_get_product_by_id_success(
        self, client: AsyncClient, test_product: Product
    ):
        """Test getting a single product by ID."""
        response = await client.get(f"/api/products/{test_product.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == test_product.id
        assert data["data"]["name"] == test_product.name

    async def test_get_product_not_found(self, client: AsyncClient):
        """Test getting non-existent product returns 404."""
        response = await client.get("/api/products/99999")

        assert response.status_code == 404

    async def test_update_product_success(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test successful product update with authentication."""
        response = await client.put(
            f"/api/products/{test_product.id}",
            json={
                "name": "Updated Laptop",
                "price": 899.99,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Laptop"
        assert data["data"]["price"] == 899.99

    async def test_update_product_without_auth(
        self, client: AsyncClient, test_product: Product
    ):
        """Test product update without authentication fails."""
        response = await client.put(
            f"/api/products/{test_product.id}",
            json={"price": 799.99},
        )

        assert response.status_code == 403

    async def test_update_product_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent product returns 404."""
        response = await client.put(
            "/api/products/99999",
            json={"price": 699.99},
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_product_success(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test successful product deletion with authentication."""
        response = await client.delete(
            f"/api/products/{test_product.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Product deleted successfully"

        # Verify product is deleted
        get_response = await client.get(f"/api/products/{test_product.id}")
        assert get_response.status_code == 404

    async def test_delete_product_without_auth(
        self, client: AsyncClient, test_product: Product
    ):
        """Test product deletion without authentication fails."""
        response = await client.delete(f"/api/products/{test_product.id}")

        assert response.status_code == 403

    async def test_delete_product_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent product returns 404."""
        response = await client.delete(
            "/api/products/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
