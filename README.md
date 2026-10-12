# FastAPI Sample Project

A FastAPI sample project demonstrating best practices for building RESTful APIs with Python.

##  Features

- **RESTful API** - Products CRUD with cursor pagination, ETag/If-Match concurrency and Idempotency-Key retries
- **JWT Authentication** - Registration and login with bcrypt-hashed passwords
- **Hexagonal architecture** - Pure domain and use cases, adapters at the edges; layer boundaries enforced by `make lint`
- **Async PostgreSQL** - SQLAlchemy 2 (async) with psycopg 3; Alembic migrations
- **Contract-first** - `openapi.yaml` is the source of truth; Pydantic models are generated from it
- **Problem Details errors** - RFC 7807 responses with stable error codes
- **Containerized development** - One image for every environment; an attachable debugger, with editing from a local uv environment or a VS Code dev container
- **Tested and type-checked** - pytest (~90% coverage), pyright over app and tests, ruff, import-linter

##  Technology Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.13 |
| **Web Framework** | FastAPI 0.142 on Uvicorn |
| **ORM** | SQLAlchemy 2.1 (async) |
| **Database** | PostgreSQL 18, psycopg 3 driver (compiled C implementation) |
| **Migrations** | Alembic |
| **Validation** | Pydantic 2, models generated from OpenAPI with datamodel-code-generator |
| **Authentication** | JWT (python-jose), bcrypt (passlib) |
| **Testing** | pytest with httpx |
| **Quality** | Ruff, pyright, import-linter |
| **Tooling** | Docker Compose, uv, debugpy, VS Code Dev Containers |

##  Quick Start

You need Docker (with Compose v2) and `make`; the API, database and `make`
targets run in containers. Python 3.13 and [uv](https://docs.astral.sh/uv/)
are recommended for editor support.

```bash
git clone <repository-url> && cd fast-api-sample
printf 'SECRET_KEY=%s\nDOCS_ENABLED=True\n' "$(openssl rand -hex 32)" > .env # creates (overwrites) .env
make build      # build the dev image
make up         # start PostgreSQL + the API (hot reload, debugger on :5678)
make migrate    # create the tables
make test       # run the test suite
```

The API is now at http://localhost:8000, with interactive docs at
http://localhost:8000/docs. `make help` lists every command.

For editing, run `uv sync` to create a local `.venv`, then open the folder
in VS Code. Without Python on your machine, use **Dev Containers: Reopen in
Container** instead. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#editing-in-vs-code).

##  Documentation

| Document | Read it for |
|---|---|
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Container and local setup, daily workflow, migrations, dependencies, configuration, troubleshooting |
| [docs/DEBUGGING.md](docs/DEBUGGING.md) | Attaching a debugger to the API, startup code and tests |
| [docs/STRUCTURE.md](docs/STRUCTURE.md) | Folder structure, the layers, and where new code goes |
| [docs/PROJECT.md](docs/PROJECT.md) | Walkthrough: architecture, startup, idempotent requests |
| [openapi.yaml](openapi.yaml) | The API reference: endpoints, headers, request and response schemas |

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

Generator options live in `[tool.datamodel-codegen]` in `pyproject.toml`;
`make schemas` runs `datamodel-codegen` in the dev container, and the output is
formatted with the project's Ruff configuration.

To change the API: edit `openapi.yaml`, run `make schemas`, update routes or
subclasses as needed, then run `make openapi` (which runs
`tests/test_openapi.py`; `make test ARGS="-vv tests/test_openapi.py"` shows a full diff).

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

The full API is defined in [openapi.yaml](openapi.yaml), also browsable at http://localhost:8000/docs (requires `DOCS_ENABLED=True`).

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

See [docs/DEVELOPMENT.md → Troubleshooting](docs/DEVELOPMENT.md#troubleshooting)
and [docs/DEBUGGING.md → Troubleshooting](docs/DEBUGGING.md#troubleshooting).
