"""Git history analyzer for feeding schedule and test change tracking."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Optional


def get_test_file_history(filepath: str, repo_root: str = ".") -> list[dict]:
    """Get git history for a test file.

    Returns list of dicts with 'date', 'author', 'message' keys.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--format=%aI|%an|%s", "--", filepath],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) >= 3:
            try:
                date = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
            except (ValueError, IndexError):
                continue
            entries.append({
                "date": date,
                "author": parts[1],
                "message": parts[2],
            })

    return entries


def get_code_changes_since(test_filepath: str, repo_root: str = ".") -> int:
    """Count code changes (commits to non-test files) since the last test file change."""
    try:
        # Get the date of the last change to the test file
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", test_filepath],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    if result.returncode != 0 or not result.stdout.strip():
        return 0

    try:
        last_test_change = datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
    except ValueError:
        return 0

    # Count commits to non-test files since that date
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--count",
             f"--since={last_test_change.isoformat()}",
             "--", ".", f":(exclude){test_filepath}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def get_last_test_change_date(filepath: str, repo_root: str = ".") -> Optional[datetime]:
    """Get the date of the last change to a test file."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", filepath],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        return datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def find_test_files(repo_root: str = ".") -> list[str]:
    """Find all test files in the repository."""
    test_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden and virtual env directories
        dirs[:] = [d for d in dirs if not d.startswith((".", "_", "__")) and d not in ("venv", "env", ".tox", "node_modules")]
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                test_files.append(os.path.join(root, f))
            elif f.endswith("_test.py"):
                test_files.append(os.path.join(root, f))
    return test_files


def get_module_commits(module_path: str, repo_root: str = ".") -> int:
    """Get total number of commits affecting a module path."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD", "--", module_path],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def is_git_repo(path: str = ".") -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=path,
            timeout=10,
        )
        return result.returncode == 0 and "true" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
