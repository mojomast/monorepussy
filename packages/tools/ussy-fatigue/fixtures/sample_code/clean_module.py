"""Sample clean module for testing — no cracks."""

import logging

logger = logging.getLogger(__name__)


class Calculator:
    """A simple calculator with low complexity."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Divide a by b with error handling."""
        try:
            return a / b
        except ZeroDivisionError:
            logger.warning("Division by zero attempted")
            return 0.0
