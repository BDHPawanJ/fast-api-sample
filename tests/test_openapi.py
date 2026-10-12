"""Tests for the committed OpenAPI contract."""

from pathlib import Path

import yaml

from app.api.openapi import PROBLEM_MEDIA_TYPE
from app.main import app

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"
PROBLEM_REF = "#/components/schemas/ProblemDetails"


def _operations(schema: dict):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            yield f"{method.upper()} {path}", operation


class TestOpenAPIContract:
    """Tests for openapi.yaml and the models generated from it."""

    def test_app_serves_contract(self):
        """The app's OpenAPI document should match openapi.yaml exactly."""
        contract = yaml.safe_load(OPENAPI_PATH.read_text())
        assert contract == app.openapi(), (
            "App differs from openapi.yaml. Run `pytest -vv tests/test_openapi.py` for a diff."
        )

    def test_error_responses_use_problem_details(self):
        """Every documented error response should be application/problem+json."""
        for name, operation in _operations(app.openapi()):
            for status_code, response in operation["responses"].items():
                if int(status_code) < 400:
                    continue
                content = response["content"]
                assert list(content) == [PROBLEM_MEDIA_TYPE], name
                assert content[PROBLEM_MEDIA_TYPE]["schema"]["$ref"] == PROBLEM_REF

    def test_success_responses_are_typed(self):
        """Success responses with a body should reference a component schema."""
        for name, operation in _operations(app.openapi()):
            for status_code, response in operation["responses"].items():
                if int(status_code) >= 400 or status_code == "204":
                    continue
                schema = response["content"]["application/json"]["schema"]
                assert "$ref" in schema, name

    def test_default_validation_error_schema_not_exposed(self):
        """FastAPI's HTTPValidationError should be replaced by ProblemDetails."""
        assert "HTTPValidationError" not in app.openapi()["components"]["schemas"]
