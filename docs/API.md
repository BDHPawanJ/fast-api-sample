# API Documentation

## Base URL

```
http://localhost:8000/v1
```

## Standards Applied

- Versioned API namespace (`/v1`)
- Resource-oriented URLs
- Problem Details errors (`application/problem+json`)
- Cursor pagination for collections
- Idempotency-Key for retry-safe POST operations
- ETag + If-Match for optimistic concurrency on mutable resources

## Authentication

Use JWT bearer tokens:

```
Authorization: Bearer <access_token>
```

## Endpoints

### Register User

**Endpoint:** `POST /v1/auth/register`  
**Headers:** `Idempotency-Key` (required)

Request:

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

Response `201`:

```json
{
  "user_id": "2fd3c267-e366-4cfd-99f4-6be245472585",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-09-03T13:52:10Z",
  "updated_at": "2026-09-03T13:52:10Z"
}
```

### Login

**Endpoint:** `POST /v1/auth/login`

Response `200`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "user_id": "2fd3c267-e366-4cfd-99f4-6be245472585",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2026-09-03T13:52:10Z",
    "updated_at": "2026-09-03T13:52:10Z"
  }
}
```

### Current User

**Endpoint:** `GET /v1/auth/me`  
**Auth:** Required

### Create Product

**Endpoint:** `POST /v1/products`  
**Auth:** Required  
**Headers:** `Idempotency-Key` (required)

Response `201`:

```json
{
  "product_id": "f612e6c4-6ab6-4e34-97ef-38c2b0c167f0",
  "name": "Laptop",
  "description": "High-performance laptop",
  "price": 999.99,
  "stock": 50,
  "created_at": "2026-09-03T13:55:01Z",
  "updated_at": "2026-09-03T13:55:01Z"
}
```

### List Products

**Endpoint:** `GET /v1/products`  
**Query:** `limit`, `cursor`, `search`

Response `200`:

```json
{
  "items": [],
  "next_cursor": "opaque-value",
  "has_more": true
}
```

### Get Product

**Endpoint:** `GET /v1/products/{product_id}`  
**Response Header:** `ETag`

### Update Product (Partial)

**Endpoint:** `PATCH /v1/products/{product_id}`  
**Auth:** Required  
**Header:** `If-Match` (required, value from latest `ETag`)

### Delete Product

**Endpoint:** `DELETE /v1/products/{product_id}`  
**Auth:** Required  
**Response:** `204 No Content`

### Health Endpoints

- `GET /v1/health`
- `GET /v1/health/db`
- `GET /v1/health/detailed`

## Error Format

Errors use:

```
Content-Type: application/problem+json
```

Example:

```json
{
  "type": "https://api.fastapi-sample.local/problems/precondition-failed",
  "title": "Precondition failed",
  "status": 412,
  "detail": "Resource state changed. Retrieve latest ETag and retry.",
  "instance": "/v1/products/f612e6c4-6ab6-4e34-97ef-38c2b0c167f0",
  "code": "ETAG_PRECONDITION_FAILED",
  "trace_id": "01J7T8ZX3G3G8Y5MFP2C2F8T0P"
}
```
