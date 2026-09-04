"""Structured logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime
from typing import Dict

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Formats log records as JSON objects with timestamp, level, module, and message.

    Attributes:
        None: Formatting behavior is provided through the format method.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Custom text formatter for human-readable logging.

    Formats log records as text with timestamp, level, module, and message.

    Attributes:
        None: Formatting behavior is configured through __init__.
    """

    def __init__(self):
        """
        Initialize text formatter with application-standard format.

        Returns:
            None: Constructor initializes formatter state.
        """
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
        super().__init__(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging() -> logging.Logger:
    """
    Configure and return the application logger.

    Sets up logging based on environment configuration (JSON or text format).
    Logs to both console and file.

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started")
    """
    # Get root logger
    logger = logging.getLogger("fastapi_sample")

    # Set log level from configuration
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Set formatter based on configuration
    if settings.LOG_FORMAT.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler for persistent logs
    try:
        import os
        from logging.handlers import RotatingFileHandler

        # Ensure logs directory exists
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Create rotating file handler (max 10MB per file, keep 5 backups)
        log_file = os.path.join(log_dir, f"fastapi_sample_{settings.ENVIRONMENT}.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    except Exception as e:
        # If file logging fails, just use console
        logger.warning(f"Could not setup file logging: {str(e)}")

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance for the specified module

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request")
    """
    return logging.getLogger(f"fastapi_sample.{name}")


# Initialize application logger
app_logger = setup_logging()
