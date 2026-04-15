"""Mental context capture — the 'about to type' state."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Optional

from .models import MentalContext


def capture_mental_context(
    note: str = "",
    project_dir: str = "",
) -> MentalContext:
    """Capture the developer's mental context.
    
    This includes:
    - An explicit note about what they were about to do
    - Auto-suggested context from git status
    - Current git branch
    - Git status summary
    
    Args:
        note: User-provided note about their current thinking.
        project_dir: Project directory for git context.
    """
    git_branch = _get_git_branch(project_dir)
    git_status = _get_git_status_summary(project_dir)
    auto_suggestion = _auto_suggest_context(project_dir, git_branch, git_status)

    return MentalContext(
        note=note,
        auto_suggestion=auto_suggestion,
        git_branch=git_branch,
        git_status_summary=git_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _get_git_branch(project_dir: str = "") -> str:
    """Get the current git branch name."""
    if not project_dir:
        project_dir = os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def _get_git_status_summary(project_dir: str = "") -> str:
    """Get a summary of git status."""
    if not project_dir:
        project_dir = os.getcwd()
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir,
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            if not lines:
                return "clean"
            modified = sum(1 for l in lines if l.strip().startswith("M"))
            added = sum(1 for l in lines if l.strip().startswith("A") or l.strip().startswith("??"))
            deleted = sum(1 for l in lines if l.strip().startswith("D"))
            parts = []
            if modified:
                parts.append(f"{modified} modified")
            if added:
                parts.append(f"{added} added")
            if deleted:
                parts.append(f"{deleted} deleted")
            return ", ".join(parts) if parts else f"{len(lines)} changed"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def _auto_suggest_context(project_dir: str, git_branch: str, git_status: str) -> str:
    """Auto-suggest a context note based on git state.
    
    Analyzes the current branch, modified files, and recent commits
    to suggest what the developer might be working on.
    """
    parts = []
    
    if git_branch:
        if git_branch == "main" or git_branch == "master":
            parts.append(f"On {git_branch} branch")
        else:
            parts.append(f"Working on branch: {git_branch}")
    
    if git_status and git_status != "clean":
        parts.append(f"Status: {git_status}")
    
    # Try to get the last commit message
    if project_dir:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                capture_output=True, text=True, timeout=5,
                cwd=project_dir,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts.append(f"Last commit: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, OSError):
            pass
    
    # Try to get the diff stat
    if project_dir and git_status != "clean":
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, timeout=5,
                cwd=project_dir,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Get just the summary line
                lines = result.stdout.strip().split("\n")
                if lines:
                    parts.append(f"Changes: {lines[-1].strip()}")
        except (subprocess.TimeoutExpired, OSError):
            pass

    return "; ".join(parts) if parts else ""


def format_context_display(context: MentalContext) -> str:
    """Format mental context for display on thaw.
    
    Returns a formatted string to be shown prominently when loading a snapshot.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🧠 MENTAL CONTEXT REMINDER")
    lines.append("=" * 60)
    
    if context.note:
        lines.append(f"📝 Note: {context.note}")
    
    if context.auto_suggestion:
        lines.append(f"💡 Auto-suggestion: {context.auto_suggestion}")
    
    if context.git_branch:
        lines.append(f"🌿 Branch: {context.git_branch}")
    
    if context.git_status_summary:
        lines.append(f"📊 Status: {context.git_status_summary}")
    
    if context.timestamp:
        lines.append(f"🕐 Saved at: {context.timestamp}")
    
    lines.append("=" * 60)
    return "\n".join(lines)
