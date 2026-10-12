# FastAPI Sample Project Walkthrough

How the code fits together at runtime: the architecture, what happens at
startup, and how retry-safe requests work. For the folder layout see
[STRUCTURE.md](STRUCTURE.md); to run it see [DEVELOPMENT.md](DEVELOPMENT.md).

---

## 1) What this project is

This is a **FastAPI backend service** with:
- user registration and login
- JWT-based authentication
- product APIs (create, list, get, update, delete)
- a shopping cart domain model and use cases (no HTTP endpoints yet)
- PostgreSQL database access through async SQLAlchemy (psycopg 3)
- Alembic migrations
- tests with pytest, run in Docker

Base API version path: `/v1`

---

## 2) Running it

```bash
make build && make up && make migrate
```

The full setup, daily commands and troubleshooting are in
[DEVELOPMENT.md](DEVELOPMENT.md); debugging is in [DEBUGGING.md](DEBUGGING.md).

---

## 3) Reading the code

Start with these, in order:

1. [app/main.py](../app/main.py): how the app is assembled.
2. [app/api/routes/products.py](../app/api/routes/products.py): a typical route.
3. [app/application/use_cases/products.py](../app/application/use_cases/products.py): the use cases it calls.
4. [app/domain/product.py](../app/domain/product.py): the rules they rely on.
5. [app/infrastructure/db/repositories/product.py](../app/infrastructure/db/repositories/product.py): how it is stored.
6. [app/api/deps.py](../app/api/deps.py): where the pieces are wired together.

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

`make lint` enforces this: pyright checks that every adapter satisfies its port, and import-linter rejects imports that point outward. The layers and where new code belongs are described in [STRUCTURE.md](STRUCTURE.md).

---

## 5) Startup flow (what happens when app starts)

1. Uvicorn imports [app/main.py](../app/main.py).
2. FastAPI app object is created with settings from [app/infrastructure/config.py](../app/infrastructure/config.py).
3. Middlewares are registered via [app/api/middleware/__init__.py](../app/api/middleware/__init__.py).
4. Global exception handlers are registered via [app/api/errors.py](../app/api/errors.py).
5. Versioned router (`/v1`) is attached from [app/api/v1/router.py](../app/api/v1/router.py).
6. Lifespan startup runs [app/api/lifespan.py](../app/api/lifespan.py), which initializes DB connectivity from [app/infrastructure/db/session.py](../app/infrastructure/db/session.py).

---

## 6) Idempotent requests

`POST /v1/auth/register` and `POST /v1/products` require an
`Idempotency-Key` header (any unique string, a UUID is typical). Retrying a
request with the same key and body returns the original response without
repeating the operation; reusing a key with a different body returns `409`.
The operation and the stored response are committed together, so a retry
after a failure either replays a completed request or runs it fresh.

In code: the routes in [app/api/routes/auth.py](../app/api/routes/auth.py) and
[app/api/routes/products.py](../app/api/routes/products.py) pass the operation
to `run_idempotent()` in
[app/application/idempotency.py](../app/application/idempotency.py). The use
case's own commit is deferred to that outer block (see
[app/application/unit_of_work.py](../app/application/unit_of_work.py)), which
is what puts the operation and its stored response in one transaction.
