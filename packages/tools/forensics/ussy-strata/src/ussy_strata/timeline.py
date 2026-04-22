"""Combined timeline subcommand — merges stratagit + unconformity views."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import List

from ussy_strata.core.parser import is_git_repo, parse_commits, assign_branch_names
from ussy_strata.core.survey import survey
from ussy_strata.missing_scanner import scan_repository
from ussy_strata.missing_timeline import render_timeline as render_missing_timeline


def render_combined_timeline(repo_path: str, width: int = 80, use_color: bool = True) -> str:
    """Render a combined timeline showing both stratigraphic and missing-history views."""
    if not is_git_repo(repo_path):
        return f"Error: {repo_path} is not a git repository"

    lines: List[str] = []
    lines.append("=" * width)
    lines.append("  USSY-STRATA COMBINED TIMELINE")
    lines.append("=" * width)
    lines.append("")

    # Stratigraphic view (from stratagit)
    lines.append("─" * width)
    lines.append("STRATIGRAPHIC SECTION (commits as geological strata)")
    lines.append("─" * width)
    strata = parse_commits(repo_path, max_count=50)
    if strata:
        strata = assign_branch_names(strata, repo_path)
        for s in strata[:20]:
            age = ""
            if s.date:
                days = (datetime.now(timezone.utc) - s.date).total_seconds() / 86400
                age = f"({days:.0f}d ago)"
            branch = f"[{s.branch_name}]" if s.branch_name else ""
            lines.append(f"  {s.commit_hash[:8]} {age:10s} {branch:12s} {s.message[:40]}")
        if len(strata) > 20:
            lines.append(f"  ... and {len(strata) - 20} more commits")
    else:
        lines.append("  (no commits found)")
    lines.append("")

    # Missing history view (from unconformity)
    lines.append("─" * width)
    lines.append("MISSING HISTORY (unconformities detected)")
    lines.append("─" * width)
    try:
        result = scan_repository(repo_path)
        if result.unconformities:
            timeline_output = render_missing_timeline(result, width=width)
            # Skip the header lines from the missing timeline
            for line in timeline_output.split("\n")[2:]:
                lines.append(line)
        else:
            lines.append("  No unconformities detected — history appears continuous.")
    except Exception as e:
        lines.append(f"  Could not scan for unconformities: {e}")
    lines.append("")

    lines.append("=" * width)
    return "\n".join(lines)


def timeline_main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="ussy-strata timeline",
        description="Combined geological + missing-history timeline",
    )
    parser.add_argument("-C", "--repo", default=".", help="Path to git repository")
    parser.add_argument("-w", "--width", type=int, default=80, help="Terminal width")
    parser.add_argument("--no-color", action="store_true", help="Disable colors")
    args = parser.parse_args(argv)

    repo_path = os.path.abspath(args.repo)
    output = render_combined_timeline(repo_path, width=args.width, use_color=not args.no_color)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(timeline_main())
