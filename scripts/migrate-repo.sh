#!/usr/bin/env bash
set -euo pipefail

# migrate-repo.sh — Migrate a git repository into the ussyverse monorepo
# Usage: ./scripts/migrate-repo.sh <repo_url> <target_path>
# Example: ./scripts/migrate-repo.sh https://github.com/mojomast/triageussy.git packages/tools/triage/ussy-triage

REPO_URL="${1:-}"
TARGET_PATH="${2:-}"
MONOREPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$REPO_URL" || -z "$TARGET_PATH" ]]; then
    echo "Usage: $0 <repo_url> <target_path>"
    echo "Example: $0 https://github.com/mojomast/triageussy.git packages/tools/triage/ussy-triage"
    exit 1
fi

REPO_NAME=$(basename "$REPO_URL" .git)
TEMP_DIR=$(mktemp -d)

echo "=== Migrating $REPO_NAME into monorepo ==="
echo "Target path: $TARGET_PATH"

# Check prerequisites
if ! command -v git &> /dev/null; then
    echo "Error: git is required"
    exit 1
fi

if ! python3 -c "import git_filter_repo" 2>/dev/null; then
    echo "Warning: git-filter-repo not found. Install with: pip install git-filter-repo"
    echo "Falling back to git filter-branch (slower)..."
    USE_FILTER_BRANCH=1
else
    USE_FILTER_BRANCH=0
fi

# Clone repository
echo "Cloning $REPO_URL..."
git clone --bare "$REPO_URL" "$TEMP_DIR/repo"
cd "$TEMP_DIR/repo"

# Rewrite history to subdirectory
echo "Rewriting history into $TARGET_PATH..."
if [[ "$USE_FILTER_BRANCH" -eq 0 ]]; then
    git filter-repo --to-subdirectory-filter "$TARGET_PATH" --force
else
    git filter-branch --index-filter \
        "git ls-files -s | sed \"s|\\t|\\t$TARGET_PATH/|\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info && mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\"" \
        --prune-empty --tag-name-filter cat --force -- --all
fi

# Add to monorepo
echo "Adding to monorepo..."
cd "$MONOREPO_ROOT"
git remote add "migrate-$REPO_NAME" "$TEMP_DIR/repo"
git fetch "migrate-$REPO_NAME"

# Merge with unrelated histories
git merge "migrate-$REPO_NAME/main" --allow-unrelated-histories -m "Migrate $REPO_NAME into monorepo at $TARGET_PATH"

# Cleanup
git remote remove "migrate-$REPO_NAME"
rm -rf "$TEMP_DIR"

echo "=== Migration complete ==="
echo "Verify with: git log --oneline --graph --all | head -20"
echo "Next steps:"
echo "  1. Restructure package to src/ussy_*/ layout"
echo "  2. Update pyproject.toml with new name and entry points"
echo "  3. Run tests: uv run --package <name> pytest"
