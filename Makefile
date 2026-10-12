.PHONY: help schemas schemas-check openapi format lint typecheck imports

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

schemas: ## Generate Pydantic models (app/api/schemas/generated.py) from openapi.yaml
	uv run datamodel-codegen

schemas-check: ## Fail if generated models are out of date with openapi.yaml
	uv run datamodel-codegen --check

openapi: ## Verify the app serves exactly openapi.yaml
	uv run pytest -q --no-cov tests/test_openapi.py

format: ## Sort imports and format code with ruff
	uv run ruff check --fix .
	uv run ruff format .

lint: ## Check formatting, types, and architecture layers
	uv run ruff check .
	uv run ruff format --check .
	$(MAKE) typecheck
	$(MAKE) imports

typecheck: ## Type-check app/ with pyright (includes port/adapter conformance)
	uv run pyright

imports: ## Enforce inward-only layer imports with import-linter
	uv run lint-imports
