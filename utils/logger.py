"""
Logging configuration for the AI Workflow Capture System.
Provides console and file logging with proper formatting and rotation.
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from config import Config


def setup_logging():
    """
    Configure application-wide logging.
    Creates logs directory and sets up both console and file handlers.
    """
    # Ensure logs directory exists
    Config.ensure_directories()

    # Console handler - INFO level for user feedback
    # Use UTF-8 encoding to handle special characters from third-party libraries
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # Set encoding to UTF-8 to prevent Unicode errors
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')

    # File handler with rotation - DEBUG level for detailed debugging
    file_handler = RotatingFileHandler(
        os.path.join(Config.LOGS_DIR, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'  # UTF-8 encoding for file
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    # Set Browser-Use to WARNING to suppress emoji-laden debug logs
    logging.getLogger('browser_use').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)

    logging.info("[SYSTEM] Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the module/component

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
