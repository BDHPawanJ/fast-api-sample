# FastAPI Sample Project

A FastAPI sample project demonstrating best practices for building RESTful APIs with Python. This project is designed for comparing FastAPI with other Python web frameworks like Flask and Django.

##  Features

- **RESTful API Design** - Complete CRUD operations for Products resource
- **JWT Authentication** - Secure user registration and login with JWT tokens
- **Async Database Operations** - SQLAlchemy 2.0 with async support and PostgreSQL
- **Structured Logging** - Comprehensive logging with JSON and text formats
- **Contract-Driven Responses** - Resource responses, Problem Details errors, cursor pagination
- **Type Safety** - Full type hints and Pydantic validation
- **Auto-generated Documentation** - Interactive Swagger UI and ReDoc
- **Testing Suite** - Comprehensive tests with pytest and 70%+ coverage
- **Code Quality** - Ruff for import sorting and consistent code formatting
- **Database Migrations** - Alembic for managing database schema changes

##  Requirements

- Docker with Compose v2 (runs Python 3.13, PostgreSQL 18 and all tooling)
- `make`

##  Technology Stack

| Component | Technology |
|-----------|-----------|
| **Web Framework** | FastAPI 0.109.0 |
| **Server** | Uvicorn (ASGI server) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Database** | PostgreSQL with psycopg 3 driver (async) |
| **Authentication** | JWT (python-jose) |
| **Password Hashing** | Bcrypt (passlib) |
| **Validation** | Pydantic 2.0 |
| **Migrations** | Alembic |
| **Testing** | pytest with httpx |
| **Code Formatting** | Ruff |

##  Project Structure

```
fastapi_sample/
├── app/                     # Imports point inward only: api → infrastructure → application → domain
│   ├── domain/              # Entities and business rules; pure Python, no frameworks
│   │   ├── product.py       # Product invariants and stock helpers
│   │   ├── user.py          # User account status
│   │   ├── cart.py          # Shopping cart aggregate (quantity and stock rules)
│   │   ├── idempotency.py   # Stored idempotent-request outcome
│   │   └── errors.py        # Domain errors (mapped to 404/422 by the API)
│   ├── application/         # Use cases; depend on domain + ports only
│   │   ├── ports.py         # Protocols: repositories, UnitOfWork, PasswordHasher
│   │   ├── unit_of_work.py  # Nested transactions: only the outermost block commits
│   │   ├── errors.py        # ConcurrencyConflict, IdempotencyKeyReused
│   │   ├── auth.py          # Register, authenticate, (de)activate users
│   │   ├── products.py      # Product use cases
│   │   ├── cart.py          # Cart use cases
│   │   └── idempotency.py   # run_idempotent: action + record in one transaction
│   ├── infrastructure/      # Adapters implementing the ports
│   │   ├── config.py        # Settings (environment variables)
│   │   ├── logging.py       # Logging setup
│   │   ├── db/
│   │   │   ├── base.py          # Declarative base
│   │   │   ├── session.py       # Async engine and session
│   │   │   ├── models/          # SQLAlchemy ORM models (Alembic target)
│   │   │   ├── repositories/    # ORM row ⇄ domain object mapping
│   │   │   └── unit_of_work.py  # Transaction boundary
│   │   └── security/
│   │       └── password.py  # Bcrypt PasswordHasher
│   ├── api/                 # HTTP: FastAPI routes and everything request-shaped
│   │   ├── routes/          # Auth, product and health endpoints
│   │   ├── v1/router.py     # Versioned router composition
│   │   ├── schemas/         # Generated contract models + request subclasses
│   │   ├── middleware/      # Middleware registration, request logging/timing
│   │   ├── deps.py          # Composition root: builds adapters for Depends()
│   │   ├── auth.py          # JWT tokens and get_current_user
│   │   ├── errors.py        # Exception handlers (Problem Details)
│   │   ├── lifespan.py      # Startup/shutdown hooks
│   │   ├── constants.py     # API messages and status codes
│   │   ├── pagination.py    # Cursor encode/decode
│   │   ├── problem.py       # Problem Details response helper
│   │   ├── serialization.py # Domain → response models, ETag
│   │   └── openapi.py       # OpenAPI helpers
│   └── main.py              # Application entry point
├── tests/
│   ├── conftest.py          # Pytest fixtures (real DB + UoW seeding)
│   ├── fakes.py             # In-memory ports: FakeUnitOfWork, FakePasswordHasher
│   ├── helpers.py           # must(): narrow Optional lookups in assertions
│   ├── test_domain.py       # Domain rules (no DB, no mocks)
│   ├── test_*_service.py    # Use cases against fakes
│   ├── test_repositories.py # Repositories against the test DB
│   ├── test_auth.py, test_products.py, test_health.py # HTTP endpoint tests
│   └── test_openapi.py      # OpenAPI contract tests
├── alembic/
│   ├── versions/            # Migration files
│   └── env.py               # Alembic configuration
├── .devcontainer/           # VS Code dev container (reuses the compose app service)
├── .vscode/launch.json      # Debugger attach configs (app :5678, tests :5679)
├── Dockerfile               # base → build → dev / prod (prod is the default target)
├── docker/                  # postgres/init (test DB), dev/start.sh (uvicorn + debugpy)
├── docs/
│   ├── API.md               # API documentation
│   ├── COMPARISON.md        # Framework comparison guide
│   └── PROJECT.md           # Project explainer
├── .env                     # Local environment variables 
├── compose.yaml             # Local PostgreSQL 18 service
├── Makefile                 # Schema generation, formatting, lint/typecheck/layer targets
├── openapi.yaml             # OpenAPI contract (source of truth)
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # Project metadata, dependencies and tool config
├── uv.lock                  # Locked dependency versions (managed by uv)
└── README.md                # This file
```

##  Getting Started

All development happens in Docker: the app, tests, linters and migrations run
in the `dev` image, which is the production image plus tooling. Only Docker and
`make` are needed on the host.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fastapi_sample
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root (it is bind-mounted into the dev
container and never copied into images):

```env
# JWT Secret (generate a secure key)
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# Other settings
ENVIRONMENT=development
DEBUG=True         # default: False
DOCS_ENABLED=True  # serve /docs, /redoc, /openapi.json; default: False
```

With `ENVIRONMENT=production`, `DEBUG` and `DOCS_ENABLED` are always forced off
(regardless of their values), and `/v1/health/detailed` responds 404.

`DATABASE_URL` is set by `compose.yaml` to point at the `db` container.

### 3. Start the Stack

```bash
make build    # build the dev image (again after changing dependencies)
make up       # PostgreSQL + API with hot reload
make migrate  # apply database migrations
```

The first start creates `fastapi_sample` and the test database
`fastapi_sample_test` (see `docker/postgres/init/`). Data persists in the
`db-data` volume; `docker compose down -v` wipes it.

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

`make help` lists every target; `make logs` follows the app, `make shell`
opens a shell in a dev container.

### 4. Editor (VS Code Dev Container)

Run **Dev Containers: Reopen in Container**. VS Code attaches to the same `app`
container `make up` uses (whichever starts first), and runs its Python,
Pylance, debugpy and Ruff extensions inside it, so IntelliSense, the test
explorer, formatting and the terminal all use the container's `/opt/venv`.
A host `.venv` is not needed; if one exists it is hidden inside the container.

### 5. Debugging

The dev server always runs under [debugpy](https://github.com/microsoft/debugpy)
on `localhost:5678` (bound to this machine only). In VS Code, run
**Attach: app container** from `.vscode/launch.json`; attach and detach at any
time. Breakpoints keep working across hot reloads, because the debugger follows
uvicorn's worker process. The same configuration works from the host window and
from inside the dev container.

- Breakpoints in startup code (lifespan, settings): start with
  `DEBUGPY_WAIT=1 docker compose up app`, which blocks until you attach.
- Tests: run `make test-debug ARGS=tests/test_products.py`, then
  **Attach: tests in container** (port 5679).
- Other editors: any DAP client attaching to `localhost:5678` with the path
  mapping `<repo> -> /app` works (PyCharm Professional also supports Docker
  Compose interpreters directly).

### 6. Dependencies

Edit dependencies with uv inside the container and rebuild:

```bash
make shell
uv add <pkg>        # or: uv add --dev <pkg>, uv lock --upgrade
exit
make build && make up
```

`pyproject.toml` and `uv.lock` are on the bind mount, so the change lands in
the repo; the image picks it up on rebuild.

### 7. Production Image

```bash
docker build -t fastapi-sample .   # default target: prod
```

The same image runs in every environment; configure it with environment
variables (`DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, ...). Migrations run
from the same image: `docker run --rm <env vars> fastapi-sample alembic upgrade head`.
It contains no dev tools or debugger, runs as a non-root user, and uses the
compiled psycopg driver (`PSYCOPG_IMPL=c` makes a missing build fail at start).

##  Testing

```bash
make test                                  # full suite with coverage
make test ARGS="tests/test_auth.py -v"     # specific tests
```

After running tests, open `htmlcov/index.html` for the coverage report.

##  Code Formatting

```bash
make format   # ruff: fix imports and format
make lint     # ruff + pyright + import-linter, check only (e.g. in CI)
```

##  OpenAPI Contract and Generated Models

`openapi.yaml` is the source of truth for the API. Every schema in it is
generated into `app/api/schemas/generated.py` with
[datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator).
Never edit the generated file.

- **Responses** (success and Problem Details errors) use the generated models directly.
- **Requests** use thin subclasses in `app/api/schemas/user.py` and
  `app/api/schemas/product.py` that add only logic the contract cannot express
  (password must contain a letter and a digit, prices are rounded to 2 decimals).

```bash
make schemas        # Generate Pydantic models from openapi.yaml
make schemas-check  # Fail if generated models are out of date (e.g. in CI)
make openapi        # Verify the app serves exactly openapi.yaml
```

Generator options live in `[tool.datamodel-codegen]` in `pyproject.toml`, so
`make schemas` runs `datamodel-codegen` in the dev container. The output is formatted with
the project's Ruff configuration.

To change the API: edit `openapi.yaml`, run `make schemas`, update routes or
subclasses as needed, then run `make openapi` (which runs
`tests/test_openapi.py`; use `pytest -vv` on it for a full diff).

##  API Documentation

### Quick Start - Try the API

1. **Register a new user:**

```bash
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Idempotency-Key: 7e62e9b6-4f67-45f9-b8be-4f4f9a06b173" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

2. **Login to get access token:**

```bash
curl -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

3. **Create a product (requires authentication):**

```bash
curl -X POST "http://localhost:8000/v1/products" \
  -H "Idempotency-Key: e24f3381-6800-40e4-b6d2-f04193f0f3f3" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "stock": 50
  }'
```

4. **List all products (public):**

```bash
curl "http://localhost:8000/v1/products?limit=10"
```

For complete API documentation, see [docs/API.md](docs/API.md), walkthrough [docs/PROJECT.md](docs/PROJECT.md), or visit the interactive documentation at http://localhost:8000/docs

##  Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. Register a new account at `/v1/auth/register` (with `Idempotency-Key` header)
2. Login at `/v1/auth/login` to receive an access token
3. Include the token in the Authorization header for protected endpoints:
   ```
   Authorization: Bearer <your_access_token>
   ```

### Protected vs Public Endpoints

**Public Endpoints** (no authentication required):
- `GET /v1/products` - List products (cursor pagination)
- `GET /v1/products/{product_id}` - Get single product (UUID id)
- `POST /v1/auth/register` - Register new user (requires `Idempotency-Key`)
- `POST /v1/auth/login` - Login

**Protected Endpoints** (requires authentication):
- `GET /v1/auth/me` - Get current user info
- `POST /v1/products` - Create product (requires `Idempotency-Key`)
- `PATCH /v1/products/{product_id}` - Partial update product (requires `If-Match`)
- `DELETE /v1/products/{product_id}` - Delete product


##  Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Verify PostgreSQL is running: `docker compose ps` (should be `healthy`)
2. Check databases exist: `docker compose exec db psql -U postgres -l`
3. Verify `SECRET_KEY` and other settings in `.env`
4. Rebuild after dependency changes: `make build`

### Migration Issues

If Alembic migrations fail:

```bash
# Reset migrations (this drops all tables!)
docker compose run --rm app alembic downgrade base
make migrate
```

### Import Errors

If you get import errors, the dev image is probably older than `uv.lock`:

```bash
make build && make up
```

---
