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

Hexagonal ("ports and adapters") layout. Imports only point inward:

```text
api ─────────────┐
                 ▼
infrastructure ─► application ─► domain
```

```text
Client
  -> FastAPI route (api)
     -> Depends(): get_current_user, get_uow, get_password_hasher (api/deps.py)
        -> Use case (application) talks to ports only
           -> Domain entities enforce business rules (domain)
           -> Repositories / UnitOfWork (infrastructure) map domain ⇄ ORM rows
        -> Serializers turn domain objects into response models (api)
  -> JSON response
```

Layers:
- **Domain** (`app/domain`): entities, invariants, domain errors. No framework imports.
- **Application** (`app/application`): use cases and the ports (Protocols) they need.
- **Infrastructure** (`app/infrastructure`): SQLAlchemy models, repositories, unit of work, bcrypt hasher, settings, logging.
- **API** (`app/api`): routes, schemas, middleware, JWT auth, error handlers, and the composition root that wires adapters to ports.

`make lint` enforces this: pyright checks that every adapter satisfies its port, and import-linter rejects imports that point outward.

---

## 5) Startup flow (what happens when app starts)

1. Uvicorn imports [app/main.py](../app/main.py).
2. FastAPI app object is created with settings from [app/infrastructure/config.py](../app/infrastructure/config.py).
3. Middlewares are registered via [app/api/middleware/__init__.py](../app/api/middleware/__init__.py).
4. Global exception handlers are registered via [app/api/errors.py](../app/api/errors.py).
5. Versioned router (`/v1`) is attached from [app/api/v1/router.py](../app/api/v1/router.py).
6. Lifespan startup runs [app/api/lifespan.py](../app/api/lifespan.py), which initializes DB connectivity from [app/infrastructure/db/session.py](../app/infrastructure/db/session.py).

---

## 6) Request flow (end-to-end)

### A) Register user: `POST /v1/auth/register`

Path in code:
1. Route: [app/api/routes/auth.py](../app/api/routes/auth.py)
2. Idempotency key handling: [app/application/idempotency.py](../app/application/idempotency.py)
3. Use case: [app/application/auth.py](../app/application/auth.py)
4. Password hashing adapter: [app/infrastructure/security/password.py](../app/infrastructure/security/password.py)
5. Persistence: [app/infrastructure/db/repositories/user.py](../app/infrastructure/db/repositories/user.py) → [app/infrastructure/db/models/user.py](../app/infrastructure/db/models/user.py)
6. Output shaping: [app/api/serialization.py](../app/api/serialization.py)

### B) Login: `POST /v1/auth/login`

1. Route validates credentials schema.
2. Use case verifies email + password through the `PasswordHasher` port.
3. Route creates JWT token ([app/api/auth.py](../app/api/auth.py)) and returns token + user resource.

### C) Create product: `POST /v1/products`

1. Route: [app/api/routes/products.py](../app/api/routes/products.py)
2. Auth dependency validates bearer token: [app/api/auth.py](../app/api/auth.py)
3. Use case builds a domain `Product` and adds it: [app/application/products.py](../app/application/products.py)
4. Repository persists it: [app/infrastructure/db/repositories/product.py](../app/infrastructure/db/repositories/product.py)
5. Idempotency record saved for retry-safe POST.

### D) List products: `GET /v1/products`

1. Route parses `limit`, `cursor`, `search`.
2. Cursor is decoded/encoded by [app/api/pagination.py](../app/api/pagination.py).
3. Use case queries products using `id` cursor.
4. Response returns `items`, `next_cursor`, `has_more`.

### E) Update product: `PATCH /v1/products/{product_id}`

1. Route checks `If-Match` header (ETag optimistic concurrency).
2. ETag helper from [app/api/serialization.py](../app/api/serialization.py).
3. Use case applies the partial update via `Product.update_details` (invariants enforced) and commits.

---

## 7) How important files relate to each other

### Entrypoint and composition
- [app/main.py](../app/main.py): application entrypoint, app creation, middleware, handlers, router include
- [app/api/v1/router.py](../app/api/v1/router.py): collects route modules
- [app/api/deps.py](../app/api/deps.py): composition root; builds the unit of work and password hasher for `Depends()`

### API endpoints
- [app/api/routes/auth.py](../app/api/routes/auth.py): register/login/me
- [app/api/routes/products.py](../app/api/routes/products.py): product CRUD + pagination
- [app/api/routes/health.py](../app/api/routes/health.py): app and DB health checks

### Shared runtime behavior
- [app/infrastructure/config.py](../app/infrastructure/config.py): environment and app settings
- [app/api/lifespan.py](../app/api/lifespan.py): startup/shutdown hooks
- [app/api/middleware/__init__.py](../app/api/middleware/__init__.py): CORS and custom middleware setup
- [app/api/middleware/logging.py](../app/api/middleware/logging.py): request ID logging and timing headers
- [app/api/errors.py](../app/api/errors.py): standard error response conversion, including domain errors

### Domain and use cases
- [app/domain/](../app/domain): `Product`, `User`, `Cart` entities and domain errors
- [app/application/ports.py](../app/application/ports.py): repository, `UnitOfWork` and `PasswordHasher` Protocols
- [app/application/auth.py](../app/application/auth.py): register/authenticate users
- [app/application/products.py](../app/application/products.py): product operations
- [app/application/cart.py](../app/application/cart.py): cart operations
- [app/application/idempotency.py](../app/application/idempotency.py): request replay safety

### Data and persistence
- [app/infrastructure/db/base.py](../app/infrastructure/db/base.py): SQLAlchemy declarative base
- [app/infrastructure/db/session.py](../app/infrastructure/db/session.py): async engine/session dependency
- [app/infrastructure/db/models/](../app/infrastructure/db/models): ORM tables (users, products, carts, idempotency keys)
- [app/infrastructure/db/repositories/](../app/infrastructure/db/repositories): ORM row ⇄ domain object mapping
- [app/infrastructure/db/unit_of_work.py](../app/infrastructure/db/unit_of_work.py): transaction boundary

### Contracts and response shapes
- [openapi.yaml](../openapi.yaml): OpenAPI contract, the source of truth
- [app/api/schemas/generated.py](../app/api/schemas/generated.py): request and response models generated from `openapi.yaml` by `make schemas` (options in `[tool.datamodel-codegen]` in [pyproject.toml](../pyproject.toml))
- [app/api/schemas/user.py](../app/api/schemas/user.py), [app/api/schemas/product.py](../app/api/schemas/product.py): subclasses adding custom request validation
- [app/api/serialization.py](../app/api/serialization.py): domain object to response model mapping + ETag
- [app/api/problem.py](../app/api/problem.py): RFC 7807 problem response helper

### Tests and migrations
- [tests/conftest.py](../tests/conftest.py): async test fixtures and DB override
- [tests/](../tests): domain, use case (with fakes), repository, route and config tests
- [alembic/env.py](../alembic/env.py): migration runtime setup
- [alembic/versions/](../alembic/versions): schema history

---
