"""Centralized logging configuration for ChelCheleh CMS.

This module provides a proper logging setup that replaces print() statements
with structured logging that can be configured via environment variables.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Create the main logger for the application
logger = logging.getLogger("pressassist")


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file.
        log_format: Format string for log messages.

    Returns:
        Configured logger instance.
    """
    # Parse log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure the root logger for pressassist
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Console handler - always enabled
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler - optional
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    Args:
        name: Logger name (usually module name).

    Returns:
        Child logger instance.

    Example:
        from .logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(f"pressassist.{name}")


# Pre-configured loggers for common modules
hooks_logger = get_logger("hooks")
plugins_logger = get_logger("plugins")
auth_logger = get_logger("auth")
storage_logger = get_logger("storage")
admin_logger = get_logger("admin")
