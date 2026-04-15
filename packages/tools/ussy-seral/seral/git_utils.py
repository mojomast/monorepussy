"""Git subprocess utilities for collecting repository metrics."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _run_git(args: list[str], cwd: str | Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def is_git_repo(path: str | Path) -> bool:
    """Check if path is inside a git repository."""
    try:
        _run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
        return True
    except (RuntimeError, FileNotFoundError):
        return False


def find_repo_root(path: str | Path) -> Optional[Path]:
    """Find the root of the git repository."""
    try:
        output = _run_git(["rev-parse", "--show-toplevel"], cwd=path)
        return Path(output)
    except (RuntimeError, FileNotFoundError):
        return None


def get_module_age_days(path: str | Path, repo_root: str | Path | None = None) -> float:
    """Get the age of the earliest commit touching the module in days."""
    try:
        output = _run_git(
            ["log", "--diff-filter=A", "--format=%aI", "--", str(path)],
            cwd=repo_root,
        )
        if not output:
            # Fallback: earliest commit touching this path
            output = _run_git(
                ["log", "--reverse", "--format=%aI", "--", str(path)],
                cwd=repo_root,
            )
            if not output:
                return 0.0
        # Take the last (earliest) line
        first_line = output.strip().split("\n")[-1].strip()
        first_date = datetime.fromisoformat(first_line)
        now = datetime.now(timezone.utc)
        age = (now - first_date).total_seconds() / 86400
        return max(age, 0.0)
    except (RuntimeError, ValueError, IndexError):
        return 0.0


def get_commit_count(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Get the number of commits touching a path."""
    try:
        output = _run_git(
            ["rev-list", "--count", "HEAD", "--", str(path)],
            cwd=repo_root,
        )
        return int(output) if output else 0
    except (RuntimeError, ValueError):
        return 0


def get_contributor_count(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Get the number of unique contributors to a path."""
    try:
        output = _run_git(
            ["log", "--format=%aE", "--", str(path)],
            cwd=repo_root,
        )
        if not output:
            return 0
        contributors = set(email.strip().lower() for email in output.split("\n") if email.strip())
        return len(contributors)
    except RuntimeError:
        return 0


def get_churn_rate(path: str | Path, repo_root: str | Path | None = None, weeks: int = 4) -> float:
    """Get lines changed per week over the last N weeks."""
    try:
        output = _run_git(
            ["log", f"--since={weeks}.weeks.ago", "--numstat", "--format=", "--", str(path)],
            cwd=repo_root,
        )
        total_lines = 0
        for line in output.split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    total_lines += added + deleted
                except ValueError:
                    continue
        return total_lines / weeks if weeks > 0 else 0.0
    except RuntimeError:
        return 0.0


def get_file_count(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Count tracked files in a path."""
    try:
        output = _run_git(
            ["ls-files", str(path)],
            cwd=repo_root,
        )
        if not output:
            return 0
        return len([f for f in output.split("\n") if f.strip()])
    except RuntimeError:
        return 0


def get_file_type_diversity(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Count distinct file extensions in a path."""
    try:
        output = _run_git(
            ["ls-files", str(path)],
            cwd=repo_root,
        )
        if not output:
            return 0
        extensions = set()
        for f in output.split("\n"):
            f = f.strip()
            if "." in f:
                ext = f.rsplit(".", 1)[-1].lower()
                extensions.add(ext)
        return len(extensions)
    except RuntimeError:
        return 0


def get_test_coverage(path: str | Path, repo_root: str | Path | None = None) -> float:
    """Estimate test coverage by counting test files vs source files.

    This is a heuristic: ratio of test files to total code files.
    """
    try:
        output = _run_git(
            ["ls-files", str(path)],
            cwd=repo_root,
        )
        if not output:
            return 0.0
        files = [f.strip() for f in output.split("\n") if f.strip()]
        test_files = 0
        code_files = 0
        test_patterns = ["test_", "_test.", "tests/", "spec_", "_spec.", "specs/"]
        for f in files:
            is_test = any(p in f.lower() for p in test_patterns)
            is_code = any(f.endswith(ext) for ext in (".py", ".js", ".ts", ".go", ".rs", ".java"))
            if is_test:
                test_files += 1
            if is_code:
                code_files += 1
        if code_files == 0:
            return 0.0
        return min(test_files / code_files, 1.0)
    except RuntimeError:
        return 0.0


def get_deletion_ratio(path: str | Path, repo_root: str | Path | None = None, days: int = 90) -> float:
    """Get ratio of files deleted in the last N days vs current file count."""
    try:
        # Get current file count
        current_output = _run_git(
            ["ls-files", str(path)],
            cwd=repo_root,
        )
        current_files = set(f.strip() for f in current_output.split("\n") if f.strip())

        # Get files that existed before the period
        since_ref = _run_git(
            ["log", f"--before={days}.days.ago", "-1", "--format=%H"],
            cwd=repo_root,
        )
        if not since_ref:
            return 0.0

        past_output = _run_git(
            ["ls-tree", "-r", "--name-only", since_ref, str(path)],
            cwd=repo_root,
        )
        past_files = set(f.strip() for f in past_output.split("\n") if f.strip())

        if not past_files:
            return 0.0

        deleted = past_files - current_files
        return len(deleted) / len(past_files)
    except RuntimeError:
        return 0.0


def get_contributor_spike(path: str | Path, repo_root: str | Path | None = None) -> float:
    """Detect contributor count spike as a z-score.

    Compares contributor count in last 2 weeks vs historical average.
    """
    try:
        # Recent contributors (last 2 weeks)
        recent_output = _run_git(
            ["log", "--since=2.weeks.ago", "--format=%aE", "--", str(path)],
            cwd=repo_root,
        )
        recent = set(e.strip().lower() for e in recent_output.split("\n") if e.strip())

        # Historical contributors (older than 2 weeks)
        hist_output = _run_git(
            ["log", "--before=2.weeks.ago", "--format=%aE", "--", str(path)],
            cwd=repo_root,
        )
        historical = []
        lines = hist_output.split("\n")
        # Group by some time windows to get variance
        if not lines or not any(l.strip() for l in lines):
            return 0.0

        # Simple approach: if recent count is much higher than expected
        total_historical = set(e.strip().lower() for e in lines if e.strip())
        if not total_historical:
            return float(len(recent))  # all new contributors

        expected = len(total_historical) * (14.0 / max(get_module_age_days(path, repo_root), 1.0))
        if expected == 0:
            return 0.0

        std = max(expected ** 0.5, 1.0)
        return (len(recent) - expected) / std
    except RuntimeError:
        return 0.0


def get_churn_spike(path: str | Path, repo_root: str | Path | None = None) -> float:
    """Detect churn rate spike as a z-score."""
    try:
        recent_churn = get_churn_rate(path, repo_root, weeks=2)
        overall_churn = get_churn_rate(path, repo_root, weeks=12)

        if overall_churn <= 0:
            return 0.0 if recent_churn <= 0 else recent_churn

        std = max(overall_churn ** 0.5, 1.0)
        return (recent_churn - overall_churn) / std
    except RuntimeError:
        return 0.0


def get_dependent_count(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Count modules that import from this module (heuristic via grep)."""
    try:
        module_name = Path(str(path)).name
        if not module_name:
            return 0
        # Grep for import statements referencing this module
        output = _run_git(
            ["grep", "-l", f"import.*{module_name}", "--", "*.py"],
            cwd=repo_root,
        )
        if not output:
            return 0
        files = set(f.strip() for f in output.split("\n") if f.strip())
        # Exclude files within the module itself
        external = [f for f in files if not f.startswith(str(path))]
        return len(external)
    except RuntimeError:
        return 0


def get_breaking_change_count(path: str | Path, repo_root: str | Path | None = None, days: int = 60) -> int:
    """Count commits with breaking change indicators in the last N days."""
    try:
        output = _run_git(
            [
                "log", f"--since={days}.days.ago",
                "--grep=BREAKING",
                "--grep=bump: major",
                "--grep=major!",
                "--format=%H",
                "--",
                str(path),
            ],
            cwd=repo_root,
        )
        if not output:
            return 0
        return len([l for l in output.split("\n") if l.strip()])
    except RuntimeError:
        return 0


def get_weekly_commit_history(
    path: str | Path, repo_root: str | Path | None = None, weeks: int = 52
) -> list[dict]:
    """Get commit counts per week for a path."""
    try:
        output = _run_git(
            ["log", f"--since={weeks}.weeks.ago", "--format=%aI", "--", str(path)],
            cwd=repo_root,
        )
        if not output:
            return []

        commits_by_week: dict[str, int] = {}
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                dt = datetime.fromisoformat(line)
                week_key = dt.strftime("%Y-W%W")
                commits_by_week[week_key] = commits_by_week.get(week_key, 0) + 1
            except ValueError:
                continue

        return [
            {"week": wk, "commits": ct}
            for wk, ct in sorted(commits_by_week.items())
        ]
    except RuntimeError:
        return []


def get_contributor_history(
    path: str | Path, repo_root: str | Path | None = None, weeks: int = 52
) -> list[dict]:
    """Get unique contributor count per week for a path."""
    try:
        output = _run_git(
            ["log", f"--since={weeks}.weeks.ago", "--format=%aI|%aE", "--", str(path)],
            cwd=repo_root,
        )
        if not output:
            return []

        week_contributors: dict[str, set[str]] = {}
        for line in output.split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 1)
            if len(parts) != 2:
                continue
            try:
                dt = datetime.fromisoformat(parts[0].strip())
                email = parts[1].strip().lower()
                week_key = dt.strftime("%Y-W%W")
                if week_key not in week_contributors:
                    week_contributors[week_key] = set()
                week_contributors[week_key].add(email)
            except (ValueError, IndexError):
                continue

        return [
            {"week": wk, "contributors": len(emails)}
            for wk, emails in sorted(week_contributors.items())
        ]
    except RuntimeError:
        return []
