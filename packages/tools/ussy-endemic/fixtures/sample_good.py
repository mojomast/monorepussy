# Clean Python file with good patterns
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def clean_function(data: dict) -> Optional[str]:
    """A well-typed function with proper error handling."""
    try:
        return data.get("key")
    except (KeyError, TypeError) as e:
        logger.error(f"Error processing data: {e}")
        return None


class CleanClass:
    """A class with reasonable number of methods."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}!"


class AppError(Exception):
    """Custom exception for application errors."""
    pass
