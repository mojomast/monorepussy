#!/usr/bin/env bash
set -euo pipefail

# scaffold-package.sh — Scaffold a new ussyverse package
# Usage: ./scripts/scaffold-package.sh <package_name> <category_path>
# Example: ./scripts/scaffold-package.sh mytool triage

PACKAGE_NAME="${1:-}"
CATEGORY="${2:-}"
MONOREPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$PACKAGE_NAME" || -z "$CATEGORY" ]]; then
    echo "Usage: $0 <package_name> <category>"
    echo "Example: $0 mytool triage"
    echo "Categories: forensics, security, visualization, quality, deps, triage, governance, devtools"
    exit 1
fi

# Validate package name
if [[ ! "$PACKAGE_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
    echo "Error: Package name must be lowercase alphanumeric with hyphens"
    exit 1
fi

PACKAGE_DIR="$MONOREPO_ROOT/packages/tools/$CATEGORY/ussy-$PACKAGE_NAME"
MODULE_NAME="ussy_${PACKAGE_NAME//-/_}"

echo "=== Scaffolding ussy-$PACKAGE_NAME ==="
echo "Location: $PACKAGE_DIR"

# Create directory structure
mkdir -p "$PACKAGE_DIR/src/$MODULE_NAME"
mkdir -p "$PACKAGE_DIR/tests"

# Create pyproject.toml
cat > "$PACKAGE_DIR/pyproject.toml" << EOF
[project]
name = "ussy-$PACKAGE_NAME"
version = "0.1.0"
description = "Brief description of what ussy-$PACKAGE_NAME does"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "ussy-core",
]

[project.scripts]
ussy-$PACKAGE_NAME = "$MODULE_NAME.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Create __init__.py
cat > "$PACKAGE_DIR/src/$MODULE_NAME/__init__.py" << EOF
"""$MODULE_NAME — Brief description."""

__version__ = "0.1.0"
EOF

# Create core.py
cat > "$PACKAGE_DIR/src/$MODULE_NAME/core.py" << EOF
"""Core functionality for $MODULE_NAME."""

from __future__ import annotations


def example_function() -> str:
    """Return an example string.
    
    Returns:
        A greeting message.
    """
    return "Hello from $MODULE_NAME!"
EOF

# Create cli.py
cat > "$PACKAGE_DIR/src/$MODULE_NAME/cli.py" << EOF
"""CLI entry point for $MODULE_NAME."""

from __future__ import annotations

import argparse
import sys

from $MODULE_NAME.core import example_function


def main() -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(description="ussy-$PACKAGE_NAME")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    
    args = parser.parse_args()
    
    print(example_function())
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF

# Create tests
cat > "$PACKAGE_DIR/tests/__init__.py" << EOF
"""Tests for $MODULE_NAME."""
EOF

cat > "$PACKAGE_DIR/tests/test_core.py" << EOF
"""Tests for core functionality."""

import pytest

from $MODULE_NAME.core import example_function


def test_example_function() -> None:
    """Test example_function returns expected string."""
    result = example_function()
    assert result == "Hello from $MODULE_NAME!"
EOF

cat > "$PACKAGE_DIR/tests/test_cli.py" << EOF
"""Tests for CLI."""

import subprocess
import sys

from $MODULE_NAME.cli import main


def test_cli_version() -> None:
    """Test --version flag."""
    # This is a basic test; expand as needed
    assert main is not None
EOF

# Create README.md
cat > "$PACKAGE_DIR/README.md" << EOF
# ussy-$PACKAGE_NAME

Brief description of what this tool does.

## Installation

```bash
pip install ussy-$PACKAGE_NAME
```

## Usage

```bash
ussy-$PACKAGE_NAME --help
```

## Configuration

Add to your \`pyproject.toml\`:

```toml
[tool.ussy-$PACKAGE_NAME]
# options here
```
EOF

echo "=== Scaffolding complete ==="
echo ""
echo "Next steps:"
echo "  1. Update $PACKAGE_DIR/pyproject.toml with proper description and deps"
echo "  2. Implement core functionality in $PACKAGE_DIR/src/$MODULE_NAME/core.py"
echo "  3. Add CLI commands in $PACKAGE_DIR/src/$MODULE_NAME/cli.py"
echo "  4. Run tests: uv run --package ussy-$PACKAGE_NAME pytest"
echo "  5. Add to root README.md package index"
