"""Structured logging utilities with JSONL output."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def get_logger(name: str, log_file: Path | None = None) -> logging.Logger:
    """
    Get a configured logger with both console and file handlers.

    Args:
        name: Logger name (usually __name__)
        log_file: Optional path to JSONL log file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (JSONL) if log_file provided
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = JSONLFileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    return logger


class JSONLFileHandler(logging.Handler):
    """Custom handler that writes log records as JSONL (JSON Lines)."""

    def __init__(self, filepath: Path):
        """
        Initialize JSONL file handler.

        Args:
            filepath: Path to JSONL log file
        """
        super().__init__()
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Write log record as JSON line.

        Args:
            record: Log record to write
        """
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add extra fields if present
            if hasattr(record, "extra"):
                log_entry.update(record.extra)

            # Ensure directory exists
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filepath, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception:
            # Silently fail - don't spam console with logging errors
            pass


def log_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    **kwargs: Any,
) -> None:
    """
    Log a structured event with additional metadata.

    Args:
        logger: Logger instance
        event_type: Type of event (e.g., "crawl_start", "parse_success")
        message: Human-readable message
        **kwargs: Additional metadata to include in log
    """
    extra_data = {"event_type": event_type, **kwargs}

    # Create a custom LogRecord with extra data
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(unknown file)",
        0,
        message,
        (),
        None,
    )
    record.extra = extra_data
    logger.handle(record)
