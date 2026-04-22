"""Git churn analysis — files changed frequently indicate stress."""

import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .models import ModuleMetrics


def get_git_log(path: str, since: Optional[str] = None) -> List[Dict]:
    """Get git log entries for a file or directory.

    Args:
        path: Path to file or directory.
        since: Optional date string (e.g. "6 months ago").

    Returns:
        List of dicts with 'hash', 'date', 'author' keys.
    """
    cmd = ["git", "log", "--format=%H|%ct|%an", "--follow"]
    if since:
        cmd.extend(["--since", since])
    cmd.extend(["--", path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=os.path.dirname(path) or "."
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line or "|" not in line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        try:
            ts = int(parts[1])
            entries.append({
                "hash": parts[0],
                "date": datetime.fromtimestamp(ts, tz=timezone.utc),
                "author": parts[2],
            })
        except (ValueError, OSError):
            continue
    return entries


def get_churn_for_file(filepath: str, since: Optional[str] = None) -> Tuple[float, int, int, int]:
    """Calculate churn metrics for a single file.

    Returns:
        (churn_rate, commit_count, age_days, days_since_last_change)
    """
    entries = get_git_log(filepath, since)
    commit_count = len(entries)

    if commit_count == 0:
        return 0.0, 0, 0, 0

    # Churn rate = commits per month (approximate)
    if len(entries) >= 2:
        first_date = entries[-1]["date"]
        last_date = entries[0]["date"]
        span_days = max((last_date - first_date).days, 1)
        churn_rate = (commit_count / span_days) * 30
    else:
        churn_rate = 1.0

    now = datetime.now(timezone.utc)
    first_date = entries[-1]["date"]
    age_days = max((now - first_date).days, 0)
    last_date = entries[0]["date"]
    days_since_last_change = max((now - last_date).days, 0)

    return churn_rate, commit_count, age_days, days_since_last_change


def get_all_file_churn(root_path: str, since: Optional[str] = None) -> Dict[str, Tuple[float, int, int, int]]:
    """Get churn metrics for all tracked files in a git repo.

    Returns:
        Dict mapping filepath -> (churn_rate, commit_count, age_days, days_since_last_change)
    """
    # Get list of tracked files
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, timeout=30, cwd=root_path
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    churn_data = {}

    for f in files:
        full_path = os.path.join(root_path, f)
        if not os.path.isfile(full_path):
            continue
        churn_data[f] = get_churn_for_file(full_path, since)

    return churn_data
