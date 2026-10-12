# FastAPI Sample Project Walkthrough 

---

## 1) What this project is

This is a **FastAPI backend service** with:
- user registration and login
- JWT-based authentication
- product APIs (create, list, get, update, delete)
- MySQL database access through async SQLAlchemy
- Alembic migrations
- tests with pytest

Base API version path: `/v1`

---

## 2) Quick setup commands

Run these from project root:

```bash
uv sync
```

Create `.env`:

```env
DATABASE_URL=mysql+aiomysql://<user>:<password>@localhost:3306/fastapi_sample
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=True
```

Create DBs (example):

```bash
mysql -u root -p
CREATE DATABASE fastapi_sample;
CREATE DATABASE fastapi_sample_test;
exit;
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Run server:

```bash
uv run uvicorn app.main:app --reload
```

Useful URLs:
- API root: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3) Daily developer commands

Run tests:

```bash
uv run pytest tests -v --cov=app --cov-report=term-missing --cov-report=html
```

Run specific tests:

```bash
uv run pytest tests/test_auth.py -v
uv run pytest tests/test_products.py -v
```

Format code:

```bash
make format
```

---

## 4) High-level architecture 

```text
Client
  -> FastAPI route
     -> Dependency checks (auth, db session)
        -> Service layer (business logic)
           -> SQLAlchemy models + DB
        -> Response serializers
  -> JSON response
```

Main technical layers:
- **API routes**: HTTP endpoints and request/response handling
- **Dependencies**: shared logic like authentication and DB session injection
- **Services**: business logic and DB queries
- **Models**: database tables
- **Schemas**: request/response validation with Pydantic
- **Utils**: helpers (cursor, ETag, problem response, logging)

---

## 5) Startup flow (what happens when app starts)

1. Uvicorn imports [app/main.py](../app/main.py).
2. FastAPI app object is created with settings from [app/core/config.py](../app/core/config.py).
3. Middlewares are registered via [app/core/middleware.py](../app/core/middleware.py).
4. Global exception handlers are registered via [app/api/handlers/errors.py](../app/api/handlers/errors.py).
5. Versioned router (`/v1`) is attached from [app/api/v1/router.py](../app/api/v1/router.py).
6. Lifespan startup runs [app/core/lifespan.py](../app/core/lifespan.py), which initializes DB connectivity from [app/db/session.py](../app/db/session.py).

---

## 6) Request flow (end-to-end)

### A) Register user: `POST /v1/auth/register`

Path in code:
1. Route: [app/api/routes/auth.py](../app/api/routes/auth.py)
2. Idempotency key handling: [app/services/idempotency_service.py](../app/services/idempotency_service.py)
3. Business logic: [app/services/auth_service.py](../app/services/auth_service.py)
4. Password hashing/JWT helpers: [app/core/security.py](../app/core/security.py)
5. User model table: [app/models/user.py](../app/models/user.py)
6. Output shaping: [app/utils/serialization.py](../app/utils/serialization.py)

### B) Login: `POST /v1/auth/login`

1. Route validates credentials schema.
2. Service verifies email + password.
3. Route creates JWT token and returns token + user resource.

### C) Create product: `POST /v1/products`

1. Route: [app/api/routes/products.py](../app/api/routes/products.py)
2. Auth dependency validates bearer token: [app/dependencies/auth.py](../app/dependencies/auth.py)
3. Product service creates row: [app/services/product_service.py](../app/services/product_service.py)
4. Product model: [app/models/product.py](../app/models/product.py)
5. Idempotency record saved for retry-safe POST.

### D) List products: `GET /v1/products`

1. Route parses `limit`, `cursor`, `search`.
2. Cursor is decoded/encoded by [app/utils/cursor.py](../app/utils/cursor.py).
3. Service queries products using `id` cursor.
4. Response returns `items`, `next_cursor`, `has_more`.

### E) Update product: `PATCH /v1/products/{product_id}`

1. Route checks `If-Match` header (ETag optimistic concurrency).
2. ETag helper from [app/utils/serialization.py](../app/utils/serialization.py).
3. Service applies partial update and commits.

---

## 7) How important files relate to each other

### Entrypoint and composition
- [app/main.py](../app/main.py): application entrypoint, app creation, middleware, handlers, router include
- [app/api/v1/router.py](../app/api/v1/router.py): collects route modules

### API endpoints
- [app/api/routes/auth.py](../app/api/routes/auth.py): register/login/me
- [app/api/routes/products.py](../app/api/routes/products.py): product CRUD + pagination
- [app/api/routes/health.py](../app/api/routes/health.py): app and DB health checks

### Shared runtime behavior
- [app/core/config.py](../app/core/config.py): environment and app settings
- [app/core/lifespan.py](../app/core/lifespan.py): startup/shutdown hooks
- [app/core/middleware.py](../app/core/middleware.py): CORS and custom middleware setup
- [app/middleware/logging.py](../app/middleware/logging.py): request ID logging and timing headers
- [app/api/handlers/errors.py](../app/api/handlers/errors.py): standard error response conversion

### Data and persistence
- [app/db/base.py](../app/db/base.py): SQLAlchemy declarative base
- [app/db/session.py](../app/db/session.py): async engine/session dependency
- [app/models/base.py](../app/models/base.py): common model fields
- [app/models/user.py](../app/models/user.py): users table
- [app/models/product.py](../app/models/product.py): products table
- [app/models/idempotency_key.py](../app/models/idempotency_key.py): idempotency table

### Business logic
- [app/services/auth_service.py](../app/services/auth_service.py): register/authenticate users
- [app/services/product_service.py](../app/services/product_service.py): product operations
- [app/services/idempotency_service.py](../app/services/idempotency_service.py): request replay safety

### Contracts and response shapes
- [openapi.yaml](../openapi.yaml): OpenAPI contract, the source of truth
- [app/schemas/generated.py](../app/schemas/generated.py): request and response models generated from `openapi.yaml` by `make schemas` (options in `[tool.datamodel-codegen]` in [pyproject.toml](../pyproject.toml))
- [app/schemas/user.py](../app/schemas/user.py), [app/schemas/product.py](../app/schemas/product.py): subclasses adding custom request validation
- [app/utils/serialization.py](../app/utils/serialization.py): ORM model to response model mapping + ETag
- [app/utils/problem.py](../app/utils/problem.py): RFC 7807 problem response helper

### Tests and migrations
- [tests/conftest.py](../tests/conftest.py): async test fixtures and DB override
- [tests/](../tests): route/service/security/config tests
- [alembic/env.py](../alembic/env.py): migration runtime setup
- [alembic/versions/](../alembic/versions): schema history

---
