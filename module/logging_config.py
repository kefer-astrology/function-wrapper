"""
Modern logging configuration for the module.

Provides structured logging with proper levels, formatting, and context.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.WARNING,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up modern logging configuration.
    
    Args:
        level: Logging level (default: WARNING)
        log_file: Optional file path for file logging
        format_string: Optional custom format string
        
    Returns:
        Configured root logger
    """
    # Modern format with context
    if format_string is None:
        format_string = (
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
        )
    
    # Create formatter
    formatter = logging.Formatter(
        format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add console handler
    root_logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize default logging on import
# Can be overridden by calling setup_logging() with custom settings
_setup_done = False

def ensure_logging_setup():
    """Ensure logging is set up (idempotent)."""
    global _setup_done
    if not _setup_done:
        # Default: WARNING level for production
        # Can be changed via environment variable or explicit setup
        import os
        log_level_str = os.environ.get('KEFER_LOG_LEVEL', 'WARNING').upper()
        log_level = getattr(logging, log_level_str, logging.WARNING)
        setup_logging(level=log_level)
        _setup_done = True

# Auto-setup on import
ensure_logging_setup()
