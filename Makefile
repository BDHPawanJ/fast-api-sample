.PHONY: help schemas schemas-check openapi format lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

schemas: ## Generate Pydantic models (app/schemas/generated.py) from openapi.yaml
	uv run datamodel-codegen

schemas-check: ## Fail if generated models are out of date with openapi.yaml
	uv run datamodel-codegen --check

openapi: ## Verify the app serves exactly openapi.yaml
	uv run pytest -q --no-cov tests/test_openapi.py

format: ## Sort imports and format code with ruff
	uv run ruff check --fix .
	uv run ruff format .

lint: ## Check import order and formatting with ruff
	uv run ruff check .
	uv run ruff format --check .
