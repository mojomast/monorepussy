"""Utility functions — simple, well-tested code."""


def format_name(first: str, last: str) -> str:
    """Format a full name."""
    return f"{first} {last}".strip()


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    result = []
    for char in text.lower():
        if char.isalnum():
            result.append(char)
        elif char in (" ", "-", "_"):
            result.append("-")
    return "".join(result)


def safe_divide(numerator: float, denominator: float) -> float:
    """Safely divide two numbers, returning 0 for division by zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator
