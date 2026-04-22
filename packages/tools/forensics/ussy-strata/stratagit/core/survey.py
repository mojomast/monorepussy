"""Survey — generate a geological report of the repository.

The survey command produces a comprehensive geological report,
analogous to a geological survey of a physical landscape.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from stratagit.core import (
    GeologicalReport,
    Intrusion,
    MineralType,
    Stratum,
)
from stratagit.core.parser import (
    assign_branch_names,
    classify_intrusions,
    compute_stability,
    parse_commits,
)
from stratagit.core.fossils import excavate_fossils
from stratagit.core.unconformity import detect_unconformities
from stratagit.core.fault import detect_faults


def survey(
    repo_path: str,
    max_commits: int = 0,
    include_fossils: bool = True,
    include_unconformities: bool = True,
    include_faults: bool = True,
) -> GeologicalReport:
    """Generate a geological report of the repository.

    Args:
        repo_path: Path to the git repository.
        max_commits: Max commits to analyze (0 = all).
        include_fossils: Whether to include fossil analysis.
        include_unconformities: Whether to include unconformity detection.
        include_faults: Whether to include fault line detection.

    Returns:
        GeologicalReport with all analysis results.
    """
    report = GeologicalReport(repo_path=os.path.abspath(repo_path))

    # Parse commits into strata
    try:
        strata = parse_commits(repo_path, max_count=max_commits)
    except RuntimeError:
        return report
    if not strata:
        return report

    # Assign branch names
    strata = assign_branch_names(strata, repo_path)

    # Compute stability tiers
    strata = compute_stability(strata)

    report.strata = strata
    report.total_strata = len(strata)

    # Calculate repository age
    if strata:
        dates = [s.date for s in strata if s.date]
        if dates:
            oldest = min(dates)
            report.age_days = (datetime.now(timezone.utc) - oldest).total_seconds() / 86400.0

    # Classify intrusions
    intrusions = classify_intrusions(strata)
    report.intrusions = intrusions
    report.total_intrusions = len(intrusions)

    # Mineral composition
    mineral_comp: dict[str, int] = {}
    for s in strata:
        for mineral, count in s.mineral_composition.items():
            mineral_comp[mineral] = mineral_comp.get(mineral, 0) + count
    report.mineral_composition = mineral_comp

    # Stability breakdown
    stability_breakdown: dict[str, int] = {}
    for s in strata:
        tier = s.stability_tier or "unknown"
        stability_breakdown[tier] = stability_breakdown.get(tier, 0) + 1
    report.stability_breakdown = stability_breakdown

    # Fossil analysis
    if include_fossils:
        try:
            fossils = excavate_fossils(repo_path, max_commits=max_commits or 0)
            report.fossils = fossils
            report.fossil_count = len(fossils)
        except Exception:
            pass

    # Unconformity detection
    if include_unconformities:
        try:
            unconformities = detect_unconformities(repo_path, max_commits=max_commits or 0)
            report.unconformities = unconformities
            report.unconformity_count = len(unconformities)
        except Exception:
            pass

    # Fault detection
    if include_faults:
        try:
            faults = detect_faults(repo_path)
            report.faults = faults
            report.fault_count = len(faults)
        except Exception:
            pass

    return report


def format_report(report: GeologicalReport) -> str:
    """Format a geological report as a human-readable string.

    Presents the report in geological terminology with clear
    section headers and summary statistics.
    """
    lines: List[str] = []

    lines.append("=" * 60)
    lines.append("  STRATAGIT GEOLOGICAL SURVEY REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Repository overview
    lines.append("GEOLOGICAL OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"  Location:        {report.repo_path}")
    lines.append(f"  Age:             {_format_age(report.age_days)}")
    lines.append(f"  Total strata:    {report.total_strata}")
    lines.append(f"  Intrusions:      {report.total_intrusions}")
    lines.append(f"  Unconformities:  {report.unconformity_count}")
    lines.append(f"  Fault lines:     {report.fault_count}")
    lines.append(f"  Fossils:         {report.fossil_count}")
    lines.append(f"  Fossil density:  {report.fossil_density:.2f} per 1000 strata")
    lines.append("")

    # Mineral composition
    lines.append("MINERAL COMPOSITION")
    lines.append("-" * 40)
    if report.mineral_composition:
        total = sum(report.mineral_composition.values())
        for mineral, count in sorted(
            report.mineral_composition.items(), key=lambda x: -x[1]
        ):
            pct = (count / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 2)
            lines.append(f"  {mineral:12s} {count:5d} ({pct:5.1f}%) {bar}")
    else:
        lines.append("  (no minerals detected)")
    lines.append("")

    # Dominant mineral
    lines.append(f"  Dominant mineral: {report.dominant_mineral}")
    lines.append("")

    # Stability breakdown
    lines.append("STABILITY CLASSIFICATION")
    lines.append("-" * 40)
    if report.stability_breakdown:
        for tier in ["bedrock", "mature", "settling", "active", "volatile"]:
            count = report.stability_breakdown.get(tier, 0)
            if count > 0:
                lines.append(f"  {tier:10s}: {count:5d} strata")
    else:
        lines.append("  (no stability data)")
    lines.append("")

    # Unconformities
    if report.unconformities:
        lines.append("UNCONFORMITIES (History Gaps)")
        lines.append("-" * 40)
        for u in report.unconformities[:10]:
            lines.append(
                f"  [{u.unconformity_type.value}] {u.severity} — {u.description[:60]}"
            )
        if len(report.unconformities) > 10:
            lines.append(f"  ... and {len(report.unconformities) - 10} more")
        lines.append("")

    # Fault lines
    if report.faults:
        lines.append("FAULT LINES (History Rewrites)")
        lines.append("-" * 40)
        for f in report.faults[:10]:
            lines.append(
                f"  [{f.severity_label}] {f.description[:60]}"
            )
        if len(report.faults) > 10:
            lines.append(f"  ... and {len(report.faults) - 10} more")
        lines.append("")

    # Fossils
    if report.fossils:
        lines.append("FOSSILS (Extinct Code Artifacts)")
        lines.append("-" * 40)
        for fossil in report.fossils[:10]:
            lifespan = ""
            if fossil.is_extinct and fossil.lifespan_days >= 0:
                lifespan = f" (lived {fossil.lifespan_days:.0f} days)"
            lines.append(
                f"  {fossil.kind:8s} {fossil.name:30s} in {fossil.file_path}{lifespan}"
            )
        if len(report.fossils) > 10:
            lines.append(f"  ... and {len(report.fossils) - 10} more")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def _format_age(age_days: float) -> str:
    """Format age in a human-readable geological style."""
    if age_days < 1:
        return "less than a day"
    elif age_days < 30:
        return f"{age_days:.0f} days"
    elif age_days < 365:
        return f"{age_days / 30:.1f} months"
    elif age_days < 365 * 100:
        return f"{age_days / 365:.1f} years"
    else:
        return f"{age_days / 365:.0f} years (ancient)"
