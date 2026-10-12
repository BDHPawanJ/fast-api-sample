"""Tests for product endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.product import Product

MISSING_PRODUCT_ID = "00000000-0000-0000-0000-000000000000"


def idempotency_headers(auth_headers: dict | None = None) -> dict:
    """Build headers with a fresh Idempotency-Key, plus auth if given."""
    return {**(auth_headers or {}), "Idempotency-Key": str(uuid4())}


async def get_etag(client: AsyncClient, product_id: str) -> str:
    """Fetch a product and return its current ETag."""
    response = await client.get(f"/v1/products/{product_id}")
    return response.headers["etag"]


@pytest.mark.asyncio
class TestProductEndpoints:
    """Test product CRUD API endpoints."""

    async def test_create_product_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful product creation with authentication."""
        response = await client.post(
            "/v1/products",
            json={
                "name": "New Laptop",
                "description": "A brand new laptop",
                "price": 1299.99,
                "stock": 25,
            },
            headers=idempotency_headers(auth_headers),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Laptop"
        assert data["price"] == 1299.99
        assert data["stock"] == 25
        assert "product_id" in data

    async def test_create_product_idempotent_replay(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test retrying with the same key does not create a second product."""
        headers = idempotency_headers(auth_headers)
        payload = {"name": "Retry Laptop", "price": 500.0, "stock": 1}

        first = await client.post("/v1/products", json=payload, headers=headers)
        second = await client.post("/v1/products", json=payload, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["product_id"] == first.json()["product_id"]

        listing = await client.get("/v1/products")
        assert len(listing.json()["items"]) == 1

    async def test_create_product_without_auth(self, client: AsyncClient):
        """Test product creation without authentication fails."""
        response = await client.post(
            "/v1/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": 999.99,
                "stock": 10,
            },
            headers=idempotency_headers(),
        )

        assert response.status_code == 401

    async def test_create_product_invalid_price(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test product creation with invalid price fails."""
        response = await client.post(
            "/v1/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": -100.00,
                "stock": 10,
            },
            headers=idempotency_headers(auth_headers),
        )

        assert response.status_code == 422
        fields = [error["field"] for error in response.json()["errors"]]
        assert "body -> price" in fields

    async def test_create_product_price_is_exact(
        self, client: AsyncClient, auth_headers: dict
    ):
        """A price float cannot represent exactly comes back unchanged."""
        response = await client.post(
            "/v1/products",
            json={"name": "Cable", "price": 0.1, "stock": 1},
            headers=idempotency_headers(auth_headers),
        )

        assert response.status_code == 201
        assert response.json()["price"] == 0.1
        fetched = await client.get(f"/v1/products/{response.json()['product_id']}")
        assert fetched.json()["price"] == 0.1

    async def test_create_product_price_too_large(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Prices beyond DECIMAL(10, 2) are a 422, not a database error."""
        response = await client.post(
            "/v1/products",
            json={"name": "Yacht", "price": 1e9, "stock": 1},
            headers=idempotency_headers(auth_headers),
        )

        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_PRODUCT"

    async def test_create_product_invalid_stock(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test product creation with negative stock fails."""
        response = await client.post(
            "/v1/products",
            json={
                "name": "Laptop",
                "description": "Test",
                "price": 999.99,
                "stock": -5,
            },
            headers=idempotency_headers(auth_headers),
        )

        assert response.status_code == 422
        fields = [error["field"] for error in response.json()["errors"]]
        assert "body -> stock" in fields

    async def test_list_products_success(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test listing products without authentication."""
        response = await client.get("/v1/products")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == len(test_products)
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    async def test_list_products_with_pagination(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test cursor pagination walks every product exactly once."""
        first_page = await client.get("/v1/products?limit=2")

        assert first_page.status_code == 200
        data = first_page.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"]

        seen = [item["product_id"] for item in data["items"]]
        cursor = data["next_cursor"]
        while cursor:
            page = (
                await client.get("/v1/products", params={"limit": 2, "cursor": cursor})
            ).json()
            seen.extend(item["product_id"] for item in page["items"])
            cursor = page["next_cursor"]

        assert sorted(seen) == sorted(p.public_id for p in test_products)

    async def test_list_products_invalid_cursor(self, client: AsyncClient):
        """Test an invalid cursor token is rejected."""
        response = await client.get("/v1/products?cursor=not-a-cursor")

        assert response.status_code == 400

    async def test_list_products_with_search(
        self, client: AsyncClient, test_products: list[Product]
    ):
        """Test product search functionality."""
        response = await client.get("/v1/products", params={"search": "Product 1"})

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        assert all("Product 1" in item["name"] for item in items)

    async def test_get_product_by_id_success(
        self, client: AsyncClient, test_product: Product
    ):
        """Test getting a single product by ID."""
        response = await client.get(f"/v1/products/{test_product.public_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == test_product.public_id
        assert data["name"] == test_product.name
        assert "etag" in response.headers

    async def test_get_product_not_found(self, client: AsyncClient):
        """Test getting non-existent product returns 404."""
        response = await client.get(f"/v1/products/{MISSING_PRODUCT_ID}")

        assert response.status_code == 404

    async def test_update_product_success(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test successful product update with authentication."""
        etag = await get_etag(client, test_product.public_id)

        response = await client.patch(
            f"/v1/products/{test_product.public_id}",
            json={
                "name": "Updated Laptop",
                "price": 899.99,
            },
            headers={**auth_headers, "If-Match": etag},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Laptop"
        assert data["price"] == 899.99
        assert data["stock"] == test_product.stock
        assert "etag" in response.headers

    async def test_update_product_null_name_violates_invariant(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Explicit null for a required field is rejected by the domain."""
        etag = await get_etag(client, test_product.public_id)

        response = await client.patch(
            f"/v1/products/{test_product.public_id}",
            json={"name": None},
            headers={**auth_headers, "If-Match": etag},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_PRODUCT"

    async def test_update_product_stale_etag(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test update with a stale ETag fails the precondition."""
        response = await client.patch(
            f"/v1/products/{test_product.public_id}",
            json={"price": 799.99},
            headers={**auth_headers, "If-Match": '"stale"'},
        )

        assert response.status_code == 412
        assert response.json()["code"] == "ETAG_PRECONDITION_FAILED"

    async def test_update_product_without_if_match(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test update without If-Match header fails validation."""
        response = await client.patch(
            f"/v1/products/{test_product.public_id}",
            json={"price": 799.99},
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_update_product_without_auth(
        self, client: AsyncClient, test_product: Product
    ):
        """Test product update without authentication fails."""
        etag = await get_etag(client, test_product.public_id)

        response = await client.patch(
            f"/v1/products/{test_product.public_id}",
            json={"price": 799.99},
            headers={"If-Match": etag},
        )

        assert response.status_code == 401

    async def test_update_product_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent product returns 404."""
        response = await client.patch(
            f"/v1/products/{MISSING_PRODUCT_ID}",
            json={"price": 699.99},
            headers={**auth_headers, "If-Match": '"any"'},
        )

        assert response.status_code == 404

    async def test_delete_product_success(
        self, client: AsyncClient, test_product: Product, auth_headers: dict
    ):
        """Test successful product deletion with authentication."""
        response = await client.delete(
            f"/v1/products/{test_product.public_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        assert response.content == b""

        # Verify product is deleted
        get_response = await client.get(f"/v1/products/{test_product.public_id}")
        assert get_response.status_code == 404

    async def test_delete_product_without_auth(
        self, client: AsyncClient, test_product: Product
    ):
        """Test product deletion without authentication fails."""
        response = await client.delete(f"/v1/products/{test_product.public_id}")

        assert response.status_code == 401

    async def test_delete_product_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent product returns 404."""
        response = await client.delete(
            f"/v1/products/{MISSING_PRODUCT_ID}",
            headers=auth_headers,
        )

        assert response.status_code == 404
