"""Output formatting for Assay reports."""

from __future__ import annotations

from assay.models import (
    AlloyInfo,
    Category,
    CrucibleEntry,
    FunctionAnalysis,
    GradeTrend,
    ModuleAnalysis,
    ProjectAnalysis,
    SlagItem,
    SlagReport,
)


# ── Grade report ──────────────────────────────────────────────────────────

def format_grade_report(project: ProjectAnalysis, trends: list[GradeTrend] | None = None) -> str:
    """Format a project-level grade report as a text table."""
    trend_map: dict[str, GradeTrend] = {}
    if trends:
        for t in trends:
            trend_map[t.function_name] = t

    lines: list[str] = []
    lines.append(_hline(68))
    lines.append(f"  ASSAY REPORT — {project.modules[0].file_path if project.modules else 'N/A'}")
    lines.append(_hline(68))
    lines.append(
        f"{'Function':<20} {'Lines':>6} {'Grade':>7} {'Trend':>9}  {'Composition':<20}"
    )
    lines.append(_hline(68))

    for mod in project.modules:
        for func in mod.functions:
            trend = trend_map.get(func.name)
            trend_str = f"{trend.trend_symbol} {trend.delta:+.0f}%" if trend and trend.delta != 0 else "\u2500  0%"
            bar = _grade_bar(func.grade)
            lines.append(
                f"{func.name:<20} {func.total_lines:>6} {func.grade:>6.0f}% {trend_str:>9}  {bar}"
            )

    lines.append(_hline(68))
    from assay.grade import grade_label
    lines.append(
        f"{'MODULE':<20} {project.total_lines:>6} {project.grade:>6.0f}%           {grade_label(project.grade)}"
    )
    lines.append(_hline(68))
    lines.append("  \u25a0 = business logic  \u2591 = slag/infrastructure")
    lines.append("  Grade: percentage of lines that are pure domain logic")
    return "\n".join(lines)


def _grade_bar(grade: float, width: int = 12) -> str:
    filled = round(grade / 100 * width)
    filled = max(0, min(width, filled))
    bar = "\u25a0" * filled + "\u2591" * (width - filled)
    remaining = 100 - grade
    return f"{bar} {remaining:.0f}%slag"


# ── Composition report ────────────────────────────────────────────────────

def format_compose_report(func_name: str, composition: dict) -> str:
    """Format a function's elemental composition as a text table."""
    lines: list[str] = []
    lines.append(_hline(52))
    lines.append(f"  {func_name}() — Elemental Composition")
    lines.append(_hline(52))
    lines.append(f"{'Element':<18} {'Lines':>7} {'Percentage':>11}  {'Bar':<12}")
    lines.append(_hline(52))

    total = sum(v["lines"] for v in composition.values())

    # Ordered display
    order = [
        Category.BUSINESS.value,
        Category.VALIDATION.value,
        Category.LOGGING.value,
        Category.FRAMEWORK.value,
        Category.ERROR_HANDLING.value,
        Category.SLAG.value,
        Category.UNKNOWN.value,
    ]

    for cat_val in order:
        if cat_val not in composition:
            continue
        info = composition[cat_val]
        pct = info["percentage"]
        icon = info["icon"]
        name = info["display_name"]
        bar = _compose_bar(pct)
        lines.append(
            f"  {icon} {name:<14} {info['lines']:>5} {pct:>8.1f}%  {bar}"
        )

    lines.append(_hline(52))
    lines.append(f"  {'Total':<16} {total:>5} {'100%':>9}")
    lines.append(_hline(52))
    return "\n".join(lines)


def _compose_bar(pct: float, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    filled = max(0, min(width, filled))
    return "\u25a0" * filled + "\u2591" * (width - filled)


# ── Alloy report ──────────────────────────────────────────────────────────

def format_alloy_report(alloyed: list[AlloyInfo], pure: list[FunctionAnalysis]) -> str:
    """Format the alloy detection report."""
    lines: list[str] = []

    lines.append("MIXED CONCERNS (alloyed functions):")
    if not alloyed:
        lines.append("  No alloyed functions detected.")
    for info in alloyed:
        func = info.function
        lines.append(
            f"  {func.file_path}:{func.name}() — {info.concern_count} concerns alloyed"
        )
        concerns_str = " + ".join(c.icon + " " + c.display_name for c in info.concerns_present)
        lines.append(f"    {concerns_str}")
        for sug in info.suggestions:
            lines.append(f"    Refinement: {sug}")
        lines.append(
            f"    Projected grade: {func.grade:.0f}% \u2192 {info.projected_grade:.0f}%"
        )
        lines.append("")

    lines.append("PURE FUNCTIONS (high-grade ore):")
    if not pure:
        lines.append("  No pure high-grade functions found.")
    for func in pure:
        lines.append(
            f"  {func.file_path}:{func.name}() — {func.grade:.0f}% business logic \u2b50"
        )

    return "\n".join(lines)


# ── Crucible report ───────────────────────────────────────────────────────

def format_crucible_report(crucible: dict) -> str:
    """Format the crucible map report."""
    lines: list[str] = []

    top = crucible.get("top", [])
    bottom = crucible.get("bottom", [])

    lines.append("TOP 10 MOST VALUABLE FUNCTIONS (by logic density \u00d7 usage):")
    for i, entry in enumerate(top, 1):
        emoji = _crucible_rank(entry)
        lines.append(
            f"  {i}. {entry.function.name:<20} — {entry.function.grade:.0f}% grade, "
            f"{entry.caller_count} callers — {emoji}"
        )

    lines.append("")
    lines.append("BOTTOM 10 (protection candidates — low grade):")
    for i, entry in enumerate(bottom, 1):
        lines.append(
            f"  {i}. {entry.function.name:<20} — {entry.function.grade:.0f}% grade — \u26a0\ufe0f"
        )

    return "\n".join(lines)


def _crucible_rank(entry: CrucibleEntry) -> str:
    grade = entry.function.grade
    if grade >= 80:
        return "\U0001f48e\U0001f48e\U0001f48e"
    if grade >= 60:
        return "\U0001f48e\U0001f48e"
    if grade >= 40:
        return "\U0001f48e"
    return "\u26a0\ufe0f"


# ── Slag report ───────────────────────────────────────────────────────────

def format_slag_report(report: SlagReport) -> str:
    """Format the slag inventory report."""
    lines: list[str] = []
    lines.append("SLAG INVENTORY:")

    by_type = report.by_type
    type_labels = {
        "debug_log": "Debug logging (no level check)",
        "todo_comment": "TODO/FIXME/HACK comments",
        "unreachable_branch": "Unreachable error branches",
        "commented_out": "Commented-out alternatives",
        "other_slag": "Other slag",
    }

    for slag_type, items in by_type.items():
        label = type_labels.get(slag_type, slag_type)
        lines.append(f"  {label}:")
        for item in items[:10]:
            lines.append(f"    {item.file_path}:{item.line_number:<6} — {item.content}")
        if len(items) > 10:
            lines.append(f"    ... {len(items) - 10} more instances")
        lines.append("")

    lines.append(f"Total slag: {report.total_lines} lines across {report.files_affected} files")

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────

def _hline(width: int = 68) -> str:
    return "\u2500" * width
