# syntax=docker/dockerfile:1

# One image for every environment: `prod` (the default target) is built once
# and promoted unchanged; configuration comes from environment variables.
# `dev` adds tooling and the debugger on top of the same runtime layers.

ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    # Fail at import if the compiled driver is missing instead of silently
    # falling back to the slower pure-Python implementation.
    PSYCOPG_IMPL=c
# Runtime libpq for psycopg's C implementation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
ARG UID=1000
RUN useradd --create-home --uid ${UID} app
WORKDIR /app


FROM base AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM build AS dev-build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen


FROM base AS dev
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv
# libatomic: pyright's bundled Node runtime. git/openssh-client: source control
# from the VS Code dev container (it forwards the host's SSH agent).
# procps: `ps`, used by the dev container's process/port detection.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 git openssh-client procps \
    && rm -rf /var/lib/apt/lists/* \
    # The bind-mounted repo is owned by another uid; trust it explicitly.
    && git config --system --add safe.directory /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1 \
    # Keep bytecode out of the bind-mounted tree: a host-built __pycache__
    # (e.g. pytest's assert-rewritten modules) records host paths, so the
    # debugger's /app breakpoints would never match.
    PYTHONPYCACHEPREFIX=/tmp/pycache
COPY --from=dev-build --chown=app:app /opt/venv /opt/venv
USER app
# pyright fetches its Node runtime on first use; do it at build time.
# The .vscode-server dir gives the dev container's named volume app ownership.
RUN pyright --version && mkdir -p /home/app/.vscode-server
# Source is bind-mounted at /app by compose.
EXPOSE 8000 5678
CMD ["docker/dev/start.sh"]


FROM base AS prod
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
