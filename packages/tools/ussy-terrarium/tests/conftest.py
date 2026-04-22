"""Shared test fixtures."""

collect_ignore = ["fixtures"]

import os
import json
import shutil
import tempfile
from typing import Generator

import pytest


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_PROJECT = os.path.join(FIXTURES_DIR, "sample_project")


@pytest.fixture
def sample_project_dir() -> str:
    """Return the path to the sample project fixtures."""
    return SAMPLE_PROJECT


@pytest.fixture
def temp_project_dir() -> Generator[str, None, None]:
    """Create a temporary project directory with sample Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple project structure
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir)

        # main.py
        with open(os.path.join(src_dir, "main.py"), "w") as f:
            f.write('def main():\n    print("hello")\n\nif __name__ == "__main__":\n    main()\n')

        # utils.py — simple
        with open(os.path.join(src_dir, "utils.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n")

        # complex.py — higher complexity
        with open(os.path.join(src_dir, "complex.py"), "w") as f:
            f.write(
                'def process(data):\n'
                '    if not data:\n'
                '        return None\n'
                '    if isinstance(data, str):\n'
                '        for c in data:\n'
                '            if c.isalpha():\n'
                '                pass\n'
                '            elif c.isdigit():\n'
                '                pass\n'
                '    elif isinstance(data, list):\n'
                '        for item in data:\n'
                '            try:\n'
                '                process(item)\n'
                '            except Exception:\n'
                '                pass\n'
                '    return data\n'
            )

        # deprecated_module.py
        with open(os.path.join(src_dir, "deprecated_module.py"), "w") as f:
            f.write("# DEPRECATED: do not use\ndef old_func():\n    pass\n")

        # config.py
        with open(os.path.join(src_dir, "config.py"), "w") as f:
            f.write("DEBUG = True\nPORT = 8080\n")

        # Test file
        test_dir = os.path.join(tmpdir, "tests")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test_main.py"), "w") as f:
            f.write("def test_main():\n    assert True\n")

        # Coverage file
        coverage_data = {
            "files": {
                "src/main.py": {"summary": {"covered_lines": 5, "num_statements": 6}},
                "src/utils.py": {"summary": {"covered_lines": 4, "num_statements": 4}},
                "src/complex.py": {"summary": {"covered_lines": 3, "num_statements": 12}},
            }
        }
        with open(os.path.join(tmpdir, "coverage.json"), "w") as f:
            json.dump(coverage_data, f)

        yield tmpdir


@pytest.fixture
def complex_source() -> str:
    """Python source code with various complexity levels."""
    return '''
def simple():
    return True

def moderate(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"

def complex_func(data, flag, mode):
    if not data:
        return None
    if flag:
        for item in data:
            if item > 10:
                try:
                    process(item)
                except ValueError:
                    pass
            elif item < 0:
                continue
    elif mode == "safe":
        while data:
            data.pop()
    return data
'''


@pytest.fixture
def simple_source() -> str:
    """Simple Python source code."""
    return "def hello():\n    return 'world'\n"


@pytest.fixture
def syntax_error_source() -> str:
    """Python source with syntax errors."""
    return "def broken(:\n    return\n"
