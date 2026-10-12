.PHONY: help build up down logs shell migrate test test-debug schemas schemas-check openapi format lint typecheck imports

# Every command runs in the dev container (same image layers as production).
RUN := docker compose run --rm app

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Rebuild the dev image (after changing dependencies)
	docker compose build app

up: ## Start db + app (hot reload, debugger on localhost:5678)
	docker compose up -d
	@echo "API: http://localhost:8000  |  debugger: attach to localhost:5678"

down: ## Stop all containers (data is kept in the db-data volume)
	docker compose down

logs: ## Follow app logs
	docker compose logs -f app

shell: ## Open a shell in a new dev container
	$(RUN) bash

migrate: ## Apply database migrations
	$(RUN) alembic upgrade head

test: ## Run the test suite (pass ARGS=... for pytest options or paths)
	$(RUN) pytest $(ARGS)

test-debug: ## Run tests waiting for a debugger on localhost:5679 (ARGS=...)
	docker compose run --rm -p 127.0.0.1:5679:5679 app \
		python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5679 --wait-for-client \
		-m pytest --no-cov $(ARGS)

schemas: ## Generate Pydantic models (app/api/schemas/generated.py) from openapi.yaml
	$(RUN) datamodel-codegen

schemas-check: ## Fail if generated models are out of date with openapi.yaml
	$(RUN) datamodel-codegen --check

openapi: ## Verify the app serves exactly openapi.yaml
	$(RUN) pytest -q --no-cov tests/test_openapi.py

format: ## Sort imports and format code with ruff
	$(RUN) sh -c "ruff check --fix . && ruff format ."

lint: ## Check formatting, types, and architecture layers
	$(RUN) sh -c "ruff check . && ruff format --check . && pyright && lint-imports"

typecheck: ## Type-check app/ and tests/ with pyright (includes port/adapter conformance)
	$(RUN) pyright

imports: ## Enforce inward-only layer imports with import-linter
	$(RUN) lint-imports
