"""Utility functions and helpers."""

import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def format_response(data: Any, status: str = "success") -> Dict[str, Any]:
    """Format a standard API response."""
    return {
        "status": status,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def validate_input(value: Any, rules: Dict[str, Any]) -> List[str]:
    """Validate input against a set of rules."""
    errors = []

    if "required" in rules and rules["required"] and not value:
        errors.append("Field is required")

    if "min_length" in rules and len(str(value)) < rules["min_length"]:
        errors.append(f"Must be at least {rules['min_length']} characters")

    if "max_length" in rules and len(str(value)) > rules["max_length"]:
        errors.append(f"Must be at most {rules['max_length']} characters")

    if "pattern" in rules and not re.match(rules["pattern"], str(value)):
        errors.append("Invalid format")

    return errors


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[: length - len(suffix)] + suffix


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse an ISO date string."""
    try:
        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except ValueError:
        return None


class Paginator:
    """Simple pagination helper."""

    def __init__(self, items: List[Any], page_size: int = 20):
        self.items = items
        self.page_size = page_size

    def get_page(self, page: int) -> List[Any]:
        start = (page - 1) * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    @property
    def total_pages(self) -> int:
        return (len(self.items) + self.page_size - 1) // self.page_size
