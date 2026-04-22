#!/usr/bin/env bash
set -euo pipefail

echo "=== Ussyverse Bootstrap ==="

# Install uv if missing
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "Syncing dependencies..."
uv sync --extra all --group dev

echo "Running tests..."
uv run pytest -n auto

echo "Bootstrap complete!"
