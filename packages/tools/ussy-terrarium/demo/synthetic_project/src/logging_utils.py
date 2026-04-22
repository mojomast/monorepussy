"""Logging and observability utilities."""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO"):
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


class StructuredLogger:
    """Logger that outputs structured JSON logs."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str, **kwargs):
        self.logger.info(f"{message} | {kwargs}")

    def warning(self, message: str, **kwargs):
        self.logger.warning(f"{message} | {kwargs}")

    def error(self, message: str, **kwargs):
        self.logger.error(f"{message} | {kwargs}")

    def debug(self, message: str, **kwargs):
        self.logger.debug(f"{message} | {kwargs}")


def log_request(environ: dict, status: str, duration: float):
    """Log an HTTP request."""
    logger = StructuredLogger("http")
    logger.info(
        "Request",
        method=environ.get("REQUEST_METHOD"),
        path=environ.get("PATH_INFO"),
        status=status,
        duration=f"{duration:.4f}s",
    )
