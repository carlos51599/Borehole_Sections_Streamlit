"""
Centralized logging configuration.
"""

import logging
import sys
from typing import Optional
from pathlib import Path


class CustomFormatter(logging.Formatter):
    """Custom formatter that adjusts format based on log level."""

    def format(self, record):
        if record.levelno >= logging.ERROR:
            # Include file and line for errors
            fmt = "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s"
        elif record.levelno == logging.WARNING:
            # Warnings with component name
            fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        else:
            # Info messages are kept minimal
            fmt = "%(asctime)s %(levelname)s %(message)s"

        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(debug: bool = False, log_file: Optional[str] = None):
    """
    Configure logging for the entire application.

    Args:
        debug: If True, set log level to DEBUG
        log_file: Optional file path to write logs to
    """
    # Reset any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Configure root logger for warnings and errors only
    root.setLevel(logging.WARNING)

    # Create console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.WARNING)
    console.setFormatter(CustomFormatter())
    root.addHandler(console)

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(CustomFormatter())
        root.addHandler(file_handler)

    # Prevent propagation for noisy libraries
    for name in ["streamlit", "PIL", "matplotlib", "urllib3", "requests", "asyncio"]:
        logging.getLogger(name).propagate = False
