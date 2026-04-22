#!/usr/bin/env bash
set -euo pipefail

PACKAGE="${1:-}"
if [[ -z "$PACKAGE" ]]; then
    echo "Usage: $0 <package-name>"
    exit 1
fi

echo "Releasing $PACKAGE..."

# Validate
uv run pytest packages/"$PACKAGE" -n auto
uv run ruff check packages/"$PACKAGE"
uv run mypy packages/"$PACKAGE"

# Build and publish
cd packages/"$PACKAGE"
uv build
uv publish

echo "Release of $PACKAGE complete!"
