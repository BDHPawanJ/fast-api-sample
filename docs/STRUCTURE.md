# Project Structure

How the repository is organized, the rules that keep the layers apart, and
where new code belongs.

- [Repository layout](#repository-layout)
- [The four layers](#the-four-layers)
- [Dependency rule and how it is enforced](#dependency-rule-and-how-it-is-enforced)
- [Where does new code go?](#where-does-new-code-go)
- [Tests](#tests)
- [Container and tooling files](#container-and-tooling-files)

---

## Repository layout

```text
fast-api-sample/
├── app/                      # The application, in four layers
│   ├── domain/               #   Entities, business rules and domain errors (pure Python)
│   ├── application/          #   Ports (Protocols), unit of work base, idempotency
│   │   └── use_cases/        #     Use cases, one module per feature area
│   ├── infrastructure/       #   Adapters: settings, logging, database, password hashing
│   │   ├── db/               #     Engine/session, unit of work
│   │   │   ├── models/       #       ORM tables (what Alembic migrates)
│   │   │   └── repositories/ #       ORM rows ⇄ domain objects, one per aggregate
│   │   └── security/         #     Bcrypt PasswordHasher
│   └── api/                  #   HTTP: auth, error handlers, serialization, composition root
│       ├── v1/               #     Mounts the routes under /v1
│       │   └── routes/       #     Endpoint handlers for /v1
│       ├── schemas/          #     Pydantic models generated from openapi.yaml + request subclasses
│       └── middleware/       #     Middleware registration, request logging and timing
├── tests/                    # Unit, integration and HTTP tests, plus fakes
├── alembic/                  # Migration environment
│   └── versions/             #   Migrations, applied in order
├── docker/
│   ├── dev/                  # Dev server start script (uvicorn under debugpy)
│   └── postgres/init/        # SQL run on the database's first start
├── .devcontainer/            # VS Code dev container configuration
├── .vscode/                  # Debugger launch configurations, recommended extensions
└── docs/                     # This documentation
```

The files at the top level (`Dockerfile`, `compose.yaml`, `Makefile`,
`openapi.yaml`, `pyproject.toml`, ...) are described in
[Container and tooling files](#container-and-tooling-files).

---

## The four layers

The application follows a hexagonal ("ports and adapters") layout. Business
rules sit in the middle and know nothing about HTTP or databases; everything
that talks to the outside world sits at the edges.

| Layer | Package | Contains | May import |
|---|---|---|---|
| **Domain** | `app/domain` | Entities (`Product`, `User`, `Cart`), their invariants, domain errors | Standard library only |
| **Application** | `app/application` | Use cases (`create_product`, `add_to_cart`, ...) and **ports**: the `Protocol`s they need (`UnitOfWork`, repositories, `PasswordHasher`) | Domain |
| **Infrastructure** | `app/infrastructure` | **Adapters** implementing the ports: SQLAlchemy models and repositories, the unit of work, the bcrypt hasher; settings and logging | Application, domain |
| **API** | `app/api` | FastAPI routes, request/response schemas, middleware, JWT, error handlers, and the composition root | Everything |

A request flows inward and back out:

```text
HTTP request
  → route (api)                         parses and validates the request
    → Depends(): get_uow, get_password_hasher, get_current_user (api/deps.py, api/auth.py)
      → use case (application)          talks only to ports
        → domain entities               enforce the business rules
        → repositories / unit of work   (infrastructure) map domain objects ⇄ rows
    ← serializer (api)                  turns domain objects into response models
HTTP response
```

Some properties of this design that are easy to miss:

- **Domain objects are plain dataclasses, not ORM models.** Repositories copy
  data between ORM rows and domain objects, so domain code can be unit-tested
  without a database, and changing a table never forces a change to business
  rules.
- **The unit of work owns the transaction.** Use cases call `uow.commit()`;
  nothing else commits. Blocks nest, so `run_idempotent()` can wrap a use case
  and both commit together (see `app/application/unit_of_work.py`).
- **`app/api/deps.py` is the only place that constructs adapters.** Routes ask
  for ports; tests replace them through `app.dependency_overrides` or by
  passing fakes directly to use cases.
- **Money is `Decimal`.** Prices are exact and in whole cents inside the
  domain and database; the API converts at the boundary (JSON stays a number).

---

## Dependency rule and how it is enforced

Imports only point inward:

```text
api ─────────────┐
                 ▼
infrastructure ─► application ─► domain
```

`make lint` checks this automatically, so a violation fails CI rather than
waiting for code review:

- **import-linter** (`[tool.importlinter]` in `pyproject.toml`) enforces the
  layer order, and forbids `sqlalchemy`, `fastapi`, `starlette`, `pydantic`,
  `passlib` and `jose` in `domain` and `application`.
- **pyright** type-checks `app/` and `tests/`. Because routes receive adapters
  typed as their ports, it also proves each adapter (and each test fake)
  matches its `Protocol`, like a Go compiler checking an interface.

---

## Where does new code go?

| You are adding... | Put it in | Notes |
|---|---|---|
| A business rule ("a cart line can't exceed stock") | `app/domain/<entity>.py` | Raise a `DomainError` subclass from `app/domain/errors.py`; the API maps it to 404/422 automatically |
| A new operation ("apply a coupon") | `app/application/use_cases/<area>.py` | A function taking `uow` (and other ports); open `async with uow:` and call `uow.commit()` |
| Something a use case needs from outside (email, payment provider, clock) | A `Protocol` in `app/application/ports.py`, an implementation in `app/infrastructure/`, wiring in `app/api/deps.py` | Add a fake to `tests/fakes.py` |
| A new table or column | `app/infrastructure/db/models/`, then a migration in `alembic/versions/` | See [DEVELOPMENT.md → Database and migrations](DEVELOPMENT.md#database-and-migrations) |
| Persistence for a new aggregate | `app/infrastructure/db/repositories/<aggregate>.py` + a property on the unit of work | Map rows to domain objects; translate DB errors into application errors |
| A new endpoint | `openapi.yaml` first, then `make schemas`, then `app/api/routes/` | The contract is the source of truth; `make openapi` verifies the app matches it |
| Request validation the contract can't express | A subclass in `app/api/schemas/` | Keep it thin; business rules belong in the domain |
| A setting | `app/infrastructure/config.py` | Read it in `api/` or `infrastructure/`, never in `domain/` or `application/`; pass values in instead |

---

## Tests

| File | What it tests | Needs the database? |
|---|---|---|
| `test_domain.py` | Entity rules | No |
| `test_*_service.py`, `test_unit_of_work.py` | Use cases and transaction semantics, against in-memory fakes | No |
| `test_repositories.py` | Repositories, real transactions, rollback and race handling | Yes |
| `test_auth.py`, `test_products.py`, `test_health.py`, ... | HTTP endpoints end to end | Yes |
| `test_openapi.py` | The served OpenAPI document equals `openapi.yaml` | No |

Supporting files:

- `conftest.py`: creates the tables in `fastapi_sample_test` for each test,
  and fixtures that seed data through the real unit of work.
- `fakes.py`: `FakeUnitOfWork` (with the real nesting semantics) and
  `FakePasswordHasher`.
- `helpers.py`: `must()`, which narrows `X | None` to `X` in assertions.

---

## Container and tooling files

| File | Role |
|---|---|
| `Dockerfile` | `base` (Python + libpq) → `build` (compiles dependencies) → `dev` (adds dev tools, debugpy, git) and `prod` (the default target, shipped to every environment) |
| `compose.yaml` | `app` runs the dev image with the repo bind-mounted at `/app`; `db` is PostgreSQL 18 with a persistent `db-data` volume |
| `docker/dev/start.sh` | Starts uvicorn with auto-reload under debugpy |
| `.devcontainer/devcontainer.json` | Lets VS Code run its Python tooling inside the `app` container |
| `.vscode/launch.json` | Debugger configurations; see [DEBUGGING.md](DEBUGGING.md) |
| `Makefile` | Wraps every command in `docker compose run`; `make help` lists them |
| `openapi.yaml` | The API contract; the source of truth for request and response schemas |
| `pyproject.toml`, `uv.lock` | Dependencies (locked by uv) and tool configuration: pytest, ruff, pyright, import-linter, codegen |
| `alembic.ini` | Alembic settings; the database URL comes from the app settings |
| `.dockerignore` | Keeps `.env`, caches and any `.venv` out of images |
| `.env` | Local settings; not committed, never baked into an image |

The container setup itself is explained in [DEVELOPMENT.md](DEVELOPMENT.md).
