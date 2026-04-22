"""Simple Python module for testing pattern extraction."""

import os
import sys
from typing import List, Optional


def simple_function(x: int) -> int:
    """A simple function with low complexity."""
    return x + 1


def complex_function(data: List[int], threshold: float = 0.5) -> Optional[int]:
    """A more complex function with branching and loops."""
    result = 0
    for item in data:
        if item > threshold:
            result += item
        elif item < 0:
            try:
                result += abs(item)
            except TypeError:
                result = 0
        else:
            result -= 1

    if result > 100:
        return result
    elif result > 50:
        return int(result)
    else:
        return None


class SimpleClass:
    """A simple class."""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}!"


class DataProcessor:
    """A class with multiple methods."""

    def __init__(self, config: dict):
        self.config = config
        self.data = []

    def process(self, items: List[str]) -> List[str]:
        results = []
        for item in items:
            if self._validate(item):
                results.append(self._transform(item))
        return results

    def _validate(self, item: str) -> bool:
        return len(item) > 0 and item.isalpha()

    def _transform(self, item: str) -> str:
        return item.upper()


def bare_except_function():
    """Function with bare except — typically anomalous."""
    try:
        risky_operation()
    except:
        pass


def global_using_function():
    """Function using global variables."""
    global SOME_GLOBAL
    SOME_GLOBAL = 42
    return SOME_GLOBAL


SOME_GLOBAL = 0


def risky_operation():
    """Placeholder for risky operation."""
    raise ValueError("not implemented")
