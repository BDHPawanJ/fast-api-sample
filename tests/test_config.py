"""Unit tests for application settings."""

import pytest

from app.infrastructure.config import Settings


def test_parse_cors_origins_from_string():
    """CORS origins string should be parsed to clean list."""
    cfg = Settings(CORS_ORIGINS="http://a.com, http://b.com ,")
    assert cfg.CORS_ORIGINS == ["http://a.com", "http://b.com"]
    assert cfg.cors_origins_list == ["http://a.com", "http://b.com"]


def test_parse_cors_origins_empty_string():
    """Empty CORS origins string should become empty list."""
    cfg = Settings(CORS_ORIGINS="")
    assert cfg.CORS_ORIGINS == []
    assert cfg.cors_origins_list == []


def test_environment_properties():
    """Environment helper properties should match selected environment."""
    dev_cfg = Settings(ENVIRONMENT="development")
    assert dev_cfg.is_development is True
    assert dev_cfg.is_testing is False
    assert dev_cfg.is_production is False

    test_cfg = Settings(ENVIRONMENT="testing")
    assert test_cfg.is_development is False
    assert test_cfg.is_testing is True
    assert test_cfg.is_production is False

    prod_cfg = Settings(ENVIRONMENT="production")
    assert prod_cfg.is_development is False
    assert prod_cfg.is_testing is False
    assert prod_cfg.is_production is True


def test_debug_and_docs_default_to_disabled():
    """DEBUG and DOCS_ENABLED should be off unless explicitly enabled."""
    # _env_file is a pydantic-settings init option missing from the typed signature.
    cfg = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert cfg.DEBUG is False
    assert cfg.DOCS_ENABLED is False


def test_debug_and_docs_can_be_enabled_outside_production():
    """Non-production environments should honor DEBUG and DOCS_ENABLED."""
    cfg = Settings(ENVIRONMENT="development", DEBUG=True, DOCS_ENABLED=True)
    assert cfg.DEBUG is True
    assert cfg.DOCS_ENABLED is True


def test_debug_and_docs_forced_off_in_production():
    """Production should disable DEBUG and DOCS_ENABLED even if set to true."""
    cfg = Settings(ENVIRONMENT="production", DEBUG=True, DOCS_ENABLED=True)
    assert cfg.DEBUG is False
    assert cfg.DOCS_ENABLED is False


def test_db_url_uses_test_database_in_testing():
    """db_url should use test database URL when in testing environment."""
    cfg = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="******prod-host/prod_db",
        TEST_DATABASE_URL="******test-host/test_db",
    )
    assert cfg.db_url == "******test-host/test_db"


def test_db_url_falls_back_to_database_url():
    """db_url should use DATABASE_URL when test URL is unavailable."""
    cfg = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="******prod-host/prod_db",
        TEST_DATABASE_URL=None,
    )
    assert cfg.db_url == "******prod-host/prod_db"


def test_validate_log_level_raises_for_invalid_value():
    """Invalid log level should raise validation error."""
    with pytest.raises(ValueError):
        Settings(LOG_LEVEL="verbose")
