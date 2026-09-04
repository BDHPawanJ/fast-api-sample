"""Application configuration management using Pydantic Settings."""

from typing import Any, List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        APP_NAME: Application name
        APP_VERSION: Application version
        ENVIRONMENT: Current environment (development, testing, production)
        DEBUG: Debug mode flag
        HOST: Server host
        PORT: Server port
        DATABASE_URL: Database connection URL
        DATABASE_POOL_SIZE: Database connection pool size
        DATABASE_MAX_OVERFLOW: Maximum database connection overflow
        TEST_DATABASE_URL: Test database connection URL
        SECRET_KEY: Secret key for JWT encoding/decoding
        ALGORITHM: JWT algorithm
        ACCESS_TOKEN_EXPIRE_MINUTES: JWT token expiration time in minutes
        CORS_ORIGINS: List of allowed CORS origins
        CORS_ALLOW_CREDENTIALS: Allow credentials in CORS
        CORS_ALLOW_METHODS: Allowed HTTP methods in CORS
        CORS_ALLOW_HEADERS: Allowed headers in CORS
        LOG_LEVEL: Logging level
        LOG_FORMAT: Logging format (json or text)
        DEFAULT_PAGE_SIZE: Default pagination page size
        MAX_PAGE_SIZE: Maximum pagination page size
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_parse_none_str="null",
    )

    # Application Settings
    APP_NAME: str = "FastAPI Sample Project"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/fastapi_sample"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    TEST_DATABASE_URL: Optional[str] = None

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Settings - using str to avoid JSON parsing, then converting to list
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:8000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str], Any]) -> List[str]:
        """
        Parse CORS origins value into a normalized list.

        Args:
            v: Raw CORS origins input as string, list, or other type.

        Returns:
            List[str]: Normalized list of allowed origins.
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Handle empty string
            if not v or v.strip() == "":
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate and normalize configured log level.

        Args:
            v: Candidate log level string.

        Returns:
            str: Uppercased validated log level string.

        Raises:
            ValueError: If the provided log level is unsupported.
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        Validate and normalize runtime environment name.

        Args:
            v: Candidate environment string.

        Returns:
            str: Lowercased validated environment.

        Raises:
            ValueError: If the provided environment is unsupported.
        """
        valid_environments = ["development", "testing", "production"]
        v = v.lower()
        if v not in valid_environments:
            raise ValueError(f"ENVIRONMENT must be one of {valid_environments}")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Return allowed CORS origins as a normalized list.

        Returns:
            List[str]: Allowed CORS origins.
        """
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            return [
                origin.strip()
                for origin in self.CORS_ORIGINS.split(",")
                if origin.strip()
            ]
        return []

    @property
    def is_development(self) -> bool:
        """
        Check whether application is running in development mode.

        Returns:
            bool: True when ENVIRONMENT is "development".
        """
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """
        Check whether application is running in testing mode.

        Returns:
            bool: True when ENVIRONMENT is "testing".
        """
        return self.ENVIRONMENT == "testing"

    @property
    def is_production(self) -> bool:
        """
        Check whether application is running in production mode.

        Returns:
            bool: True when ENVIRONMENT is "production".
        """
        return self.ENVIRONMENT == "production"

    @property
    def db_url(self) -> str:
        """
        Resolve the active database URL for current environment.

        Returns:
            str: Test DB URL in testing mode when provided, else default DB URL.
        """
        if self.is_testing and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL


# Global settings instance
settings = Settings()
