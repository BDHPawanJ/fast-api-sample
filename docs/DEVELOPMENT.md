# Development Guide

The API and PostgreSQL run in Docker, and every `make` target runs in the
same dev image, so Docker and `make` are enough to work on the project.

Most developers also have Python on their machine. With Python 3.13 and
[uv](https://docs.astral.sh/uv/), `uv sync` creates a local `.venv` from the
same lockfile. Your editor uses it for code completion and type checking, and
you can run tests, linters and the debugger from the host without opening a
container.

- [How the setup works](#how-the-setup-works)
- [First-time setup](#first-time-setup)
- [Daily workflow](#daily-workflow)
- [Editing in VS Code](#editing-in-vs-code)
- [Database and migrations](#database-and-migrations)
- [Running tests](#running-tests)
- [Changing dependencies](#changing-dependencies)
- [Configuration](#configuration)
- [The production image](#the-production-image)
- [Troubleshooting](#troubleshooting)

Debugging has its own guide: [DEBUGGING.md](DEBUGGING.md).

---

## How the setup works

```text
your machine                         Docker (project "fast-api-sample")
────────────                         ──────────────────────────────────
editor, git, make                    app  (image fastapi-sample:dev)
.venv (uv sync, optional)              uvicorn --reload under debugpy
  │  repo bind-mounted at /app ─────►  Python env: /opt/venv
  │                                    :8000 API ── localhost:8000
  │                                    :5678 debugger ── 127.0.0.1:5678 only
  │                                      │
  │                                      ▼  postgresql+psycopg://...@db:5432
  │                                  db   (postgres:18.6-alpine)
  │                                    databases: fastapi_sample, fastapi_sample_test
  │                                    :5432 ── localhost:5432
  │                                    data: volume db-data
```

- **One image, two targets.** The `Dockerfile` builds `prod` (what every
  deployed environment runs) and `dev` (the same runtime plus pytest, ruff,
  pyright, debugpy and git). Local work uses `dev`, so dependency versions,
  the database driver and the Python build all match production.
- **Your code is mounted, not copied.** Edits on the host are visible in the
  container immediately, and uvicorn reloads on save.
- **Two Python environments, one lockfile.** The container uses `/opt/venv`,
  built into the image. Your host can have `.venv` in the repo, created by
  `uv sync`. Both are installed from `uv.lock`, so they have the same package
  versions. The host `.venv` is hidden inside the container (it holds macOS
  or Windows binaries), so the two never get mixed up.
- **Make targets are thin wrappers** around `docker compose run --rm app ...`,
  so `make test` and `docker compose run --rm app pytest` are the same thing.

---

## First-time setup

**Prerequisites:**

- Docker Desktop (or Docker Engine) with Compose v2, and `make`.
- Recommended: Python 3.13 and [uv](https://docs.astral.sh/uv/), for editor
  support and running tools on the host.
- For VS Code: the recommended extensions it offers when you open the repo.
  [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
  is optional; see [Editing in VS Code](#editing-in-vs-code).

### 1. Clone and configure

```bash
git clone <repository-url>
cd fast-api-sample
```

Create `.env` in the project root:

```env
SECRET_KEY=change-me          # generate one with: openssl rand -hex 32
ENVIRONMENT=development
DEBUG=True                    # logs SQL statements; default False
DOCS_ENABLED=True             # serves /docs, /redoc, /openapi.json; default False
```

Every setting has a default, so `.env` is optional, but without it `/docs` is
off and `SECRET_KEY` is a placeholder. `DATABASE_URL` is set by
`compose.yaml` and does not belong in `.env`. All settings are listed under
[Configuration](#configuration).

### 2. Build, start, migrate

```bash
make build     # build the dev image (a few minutes the first time)
make up        # start PostgreSQL and the API
make migrate   # create the tables
```

On its first start, the database container creates `fastapi_sample` and the
test database `fastapi_sample_test` (from `docker/postgres/init/`).

### 3. Check it works

```bash
curl http://localhost:8000/v1/health/db
# {"status":"healthy","database":"connected","database_type":"postgresql"}

make test      # the full suite should pass
```

Then open http://localhost:8000/docs (needs `DOCS_ENABLED=True`).

### 4. Create the host environment (recommended)

```bash
uv sync        # creates .venv from uv.lock, including the dev tools
```

`uv` downloads Python 3.13 if you don't have it (the version is pinned in
`.python-version`). Re-run `uv sync` whenever `uv.lock` changes, for example
after pulling.

The database driver, `psycopg[c]`, is compiled against libpq. If `uv sync`
fails while building `psycopg-c`, install the libpq headers and try again:

- macOS: `brew install libpq`, then put `$(brew --prefix libpq)/bin` on your
  `PATH` so `pg_config` is found.
- Debian/Ubuntu: `sudo apt install libpq-dev`.

---

## Daily workflow

```bash
make up            # start (no-op if already running)
make logs          # follow the API's logs
# ... edit code; the server reloads on save ...
make test          # run tests
make lint          # ruff + pyright + import-linter, as CI does
make down          # stop everything (data is kept)
```

All targets (`make help` prints this list):

| Target | What it does |
|---|---|
| `make build` | Rebuild the dev image; needed after dependency changes |
| `make up` / `make down` | Start / stop the stack; data survives `down` |
| `make logs` | Follow the API's output |
| `make shell` | Bash in a fresh dev container (run `alembic`, `uv`, `python`, ...) |
| `make migrate` | `alembic upgrade head` |
| `make test` | pytest with coverage; `ARGS="tests/test_auth.py -v"` for a subset |
| `make test-debug` | Run tests waiting for a debugger; see [DEBUGGING.md](DEBUGGING.md#debugging-tests) |
| `make format` | Fix imports and format with ruff |
| `make lint` | Check formatting, types and layer boundaries (`typecheck` and `imports` run them separately) |
| `make schemas` / `make schemas-check` | Regenerate / verify `app/api/schemas/generated.py` from `openapi.yaml` |
| `make openapi` | Verify the app serves exactly `openapi.yaml` |

Running something not covered by a target:

```bash
docker compose run --rm app <command>        # a one-off container
docker compose exec app <command>            # inside the running API container
```

### From the host

With a host `.venv`, the tools also run directly on your machine. These
commands match what `make lint` and `make test` do:

```bash
uv run pytest                                 # needs the db container: make up
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run lint-imports
```

The API itself still runs in Docker (`make up`). From the host, tests connect
to PostgreSQL on `localhost:5432`, the default `DATABASE_URL` in
`app/infrastructure/config.py`. CI and `make` are the reference: if a result on
the host differs from the container, trust the container.

---

## Editing in VS Code

There are two ways to work. Both give full code completion, type checking, the
test explorer and the debugger, and both share `.vscode/launch.json` and
`.vscode/settings.json`.

| | Host window | Dev container |
|---|---|---|
| Needs | Python 3.13 and uv on your machine | Only Docker |
| Python environment | `.venv` (`uv sync`) | `/opt/venv` in the image |
| Integrated terminal | Your own shell; `make`, `docker` and `uv run ...` work | A shell in the `app` container; run `pytest`, `alembic` directly, no `make` |
| Matches CI exactly | Same package versions; the OS differs | Yes |

### Host window

1. Run `uv sync` (see [First-time setup](#4-create-the-host-environment-recommended)).
2. Open the repo folder in VS Code and install the recommended extensions
   (Python, Pylance, Python Debugger, Ruff).
3. VS Code picks up `.venv` automatically. If it doesn't, run
   **Python: Select Interpreter** and choose `./.venv/bin/python`.

The test explorer runs pytest from `.venv` against the database container, so
start the stack with `make up` first.

### Dev container

Run **Dev Containers: Reopen in Container** from the command palette. VS Code
then runs its Python tooling (Pylance, Ruff, the test explorer and the
integrated terminal) **inside the `app` container**, against `/opt/venv`.
Use it if you don't want Python on your machine, or to check the editor sees
exactly what CI sees.

- It attaches to the same container `make up` starts; whichever you start
  first, they share one stack and one database.
- The first open downloads VS Code's server and the extensions into the
  container. They are kept in the `vscode-server` volume, so later opens and
  image rebuilds are fast.
- The integrated terminal is a shell in the container: run `pytest`, `alembic`
  or `uv` directly there, without `make`.
- Git works inside the container, and your SSH agent and Git credentials are
  forwarded automatically.
- To go back to the host window, run **Dev Containers: Reopen Folder Locally**.
  The stack keeps running.

The configuration is in `.devcontainer/devcontainer.json`. Other editors can
use the host `.venv` as their interpreter, plus `make` and the debugger port;
see
[DEBUGGING.md → Other editors](DEBUGGING.md#other-editors).

---

## Database and migrations

| | |
|---|---|
| Server | PostgreSQL 18.6, container `db` |
| From the host | `localhost:5432`, user `postgres`, password `password` |
| From containers | host `db` |
| Databases | `fastapi_sample` (app), `fastapi_sample_test` (tests) |
| Data | `db-data` volume; survives `make down`, deleted by `docker compose down -v` |

Open a SQL prompt:

```bash
docker compose exec db psql -U postgres fastapi_sample
```

### Creating a migration

1. Change or add models in `app/infrastructure/db/models/`.
2. Generate a migration, keeping the numbered revision IDs:

   ```bash
   docker compose run --rm app alembic revision --autogenerate --rev-id 006 -m "describe the change"
   ```

3. Review the generated file in `alembic/versions/`. Autogenerate is a
   starting point, not a guarantee: check column types, server defaults and
   data migrations by hand.
4. Apply it with `make migrate`, then confirm the models and the database agree:

   ```bash
   docker compose run --rm app alembic check   # "No new upgrade operations detected."
   ```

5. Check it can be undone: `docker compose run --rm app alembic downgrade -1`,
   then `make migrate` again.

Tests do not use migrations; they create tables directly from the models in
`fastapi_sample_test`, so `alembic check` is what catches a missing migration.

### Resetting the database

```bash
docker compose run --rm app alembic downgrade base && make migrate   # keep the server, drop all tables
docker compose down -v && make up && make migrate                    # wipe everything, including the test DB
```

`docker compose down -v` also deletes the `vscode-server` volume; the dev
container reinstalls it on the next open.

---

## Running tests

```bash
make test                                       # everything, with a coverage report
make test ARGS="tests/test_domain.py"           # one file
make test ARGS="-k cart -x -q"                  # by name, stop at the first failure
make test ARGS="--no-cov tests/test_products.py::TestProductEndpoints::test_create_product_success"
```

- The coverage report is written to `htmlcov/index.html` on the host.
- Tests that need the database use `fastapi_sample_test` and recreate its
  tables for every test, so they never touch your development data.
- From the host, `uv run pytest` runs the same tests against the database
  container (start it with `make up`). The VS Code test explorer does this
  too, in the host window or the dev container.

---

## Changing dependencies

Dependencies are managed with [uv](https://docs.astral.sh/uv/). With a host
`.venv`, run uv on the host:

```bash
uv add <package>          # runtime dependency
uv add --dev <package>    # development-only tool
uv lock --upgrade         # upgrade everything within the constraints in pyproject.toml
make build && make up     # rebuild the image with the new lockfile
```

`uv add` updates `pyproject.toml`, `uv.lock` and your `.venv` together. The
container doesn't see the new packages until you rebuild the image.

Without Python on the host, run the same `uv` commands in `make shell`, then
exit and rebuild. Installs made in a `make shell` container are lost when it
exits, but `pyproject.toml` and `uv.lock` are on the bind mount, so the change
still lands in the repo.

After pulling someone else's dependency changes, update both environments:
`uv sync` for the host, `make build && make up` for the container. Import
errors usually mean one of them is older than `uv.lock`.

---

## Configuration

Settings are read from environment variables, then `.env`, then the defaults
in `app/infrastructure/config.py`. Names are case-sensitive.

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` forces `DEBUG` and `DOCS_ENABLED` off and hides `/v1/health/detailed` |
| `DEBUG` | `False` | Logs every SQL statement |
| `DOCS_ENABLED` | `False` | Serves `/docs`, `/redoc` and `/openapi.json` |
| `SECRET_KEY` | placeholder | JWT signing key; must be set outside local development |
| `DATABASE_URL` | localhost URL | Set by `compose.yaml` locally; format `postgresql+psycopg://user:pass@host:5432/db` |
| `TEST_DATABASE_URL` | unset | Used by the tests; when unset, `tests/conftest.py` uses `DATABASE_URL` with the database name suffixed `_test` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | `LOG_FORMAT=text` is easier to read locally |
| `CORS_ORIGINS` | localhost:3000, :8000 | Comma-separated |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `10` / `100` | Product list pagination |
| `DEBUGPY_WAIT` | `0` | Dev only: `1` makes the API wait for a debugger before starting |

`.env` is listed in `.dockerignore`: it reaches the dev container only
through the bind mount and is never part of an image.

---

## The production image

```bash
docker build -t fastapi-sample .     # the default target is prod
```

This is the image every environment runs; only environment variables change
between them.

- No dev tools or debugger, runs as a non-root user, no `.env`.
- Uses psycopg's compiled C implementation against the system libpq.
  `PSYCOPG_IMPL=c` makes the container fail at startup if that build is
  missing, instead of silently using the slower pure-Python fallback.
- Migrations run from the same image:

  ```bash
  docker run --rm -e DATABASE_URL=... fastapi-sample alembic upgrade head
  ```

- It listens on port 8000:

  ```bash
  docker run -p 8000:8000 -e DATABASE_URL=... -e SECRET_KEY=... -e ENVIRONMENT=production fastapi-sample
  ```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `make up` starts but the API isn't reachable | `make logs`; the API waits for the database's health check, and the first start takes a few seconds |
| `ModuleNotFoundError` / import errors | An environment is older than `uv.lock`: `uv sync` on the host, `make build && make up` for the container |
| Port 8000, 5432 or 5678 already in use | Stop whatever holds it (`lsof -nP -iTCP:<port> -sTCP:LISTEN`), or change the host port in `compose.yaml` |
| Database errors in tests | Check the DB is healthy: `docker compose ps`; list databases: `docker compose exec db psql -U postgres -l` |
| `fastapi_sample_test` doesn't exist | The init script only runs on an empty volume. Create it: `docker compose exec db createdb -U postgres fastapi_sample_test` |
| Editor shows missing imports | Run `uv sync`, then **Python: Select Interpreter** → `./.venv/bin/python`; or use **Reopen in Container** |
| `uv sync` fails building `psycopg-c` | libpq headers are missing; see [First-time setup](#4-create-the-host-environment-recommended) |
| Tests on the host can't connect to the database | Start it with `make up`; tests on the host use `localhost:5432` |
| Changes aren't picked up by the server | Only `app/` is watched for reloads; for config or dependency changes run `docker compose restart app` or rebuild |
| Migrations in a bad state | `docker compose run --rm app alembic current` shows where you are; reset as described in [Resetting the database](#resetting-the-database) |
