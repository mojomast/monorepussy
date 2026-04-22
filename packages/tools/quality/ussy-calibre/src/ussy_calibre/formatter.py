"""Terminal output formatter for Levain reports.

Produces Rich-style formatted output using only stdlib (no Rich dependency).
Uses ANSI escape codes for colored terminal output.
"""

from __future__ import annotations

import json
import sys
from typing import Any

# ANSI color codes
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

# Fermentation-themed symbols
BREAD = "🍞"
YEAST = "🫧"
WARNING = "⚠️"
CHECK = "✅"
CROSS = "❌"
FLASK = "🧪"
THERMO = "🌡️"
CLOCK = "⏰"
SPREAD = "🦠"
QUARANTINE = "🏥"
SUGGEST = "💡"


def _supports_color() -> bool:
    """Check if terminal supports color."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _color(text: str, color: str) -> str:
    """Apply color if terminal supports it."""
    if _supports_color():
        return f"{color}{text}{RESET}"
    return text


def _bar(value: float, width: int = 30, filled_char: str = "█", empty_char: str = "░") -> str:
    """Create a text progress bar."""
    filled = int(value / 100 * width)
    empty = width - filled
    return filled_char * filled + empty_char * empty


def _score_color(score: float) -> str:
    """Get color based on score (0-100)."""
    if score >= 70:
        return GREEN
    elif score >= 40:
        return YELLOW
    return RED


def format_hooch(report_dict: dict) -> str:
    """Format hooch report for terminal output."""
    lines = []
    lines.append(_color(f"{BREAD} Hooch Detector — Stale Test Identification", BOLD))
    lines.append("")

    overall = report_dict["overall_hooch_index"]
    color = _score_color(100 - overall)
    lines.append(f"  Overall Hooch Index: {color}{overall:.1f}%{RESET}")
    lines.append(f"  {_bar(overall)}")
    lines.append(
        f"  Total tests: {report_dict['total_tests']} | "
        f"Hooch tests: {report_dict['hooch_count']}"
    )
    lines.append("")

    if report_dict["module_hooch_index"]:
        lines.append(_color("  Module Hooch Indices:", BOLD))
        for module, index in sorted(report_dict["module_hooch_index"].items(), key=lambda x: -x[1]):
            color = _score_color(100 - index)
            lines.append(f"    {module}: {color}{index:.1f}%{RESET}")
        lines.append("")

    if report_dict["hooch_tests"]:
        lines.append(_color("  Hooch Tests (discard candidates):", BOLD))
        for h in report_dict["hooch_tests"][:20]:
            htype = h["hooch_type"]
            symbol = {
                "dead": f"{CROSS} Dead",
                "stale": f"{WARNING} Stale",
                "dormant": f"{YEAST} Dormant",
            }.get(htype, htype)
            lines.append(f"    {symbol}: {h['name']} (confidence: {h['confidence']:.0%})")
            lines.append(f"      {DIM}{h['reason']}{RESET}")

    return "\n".join(lines)


def format_rise(report_dict: dict) -> str:
    """Format rise meter report for terminal output."""
    lines = []
    lines.append(_color(f"{YEAST} Rise Meter — Fermentation Activity Analysis", BOLD))
    lines.append("")

    score = report_dict["rise_score"]
    color = _score_color(score)
    lines.append(f"  Rise Score: {color}{score:.1f}/100{RESET}")
    lines.append(f"  {_bar(score)}")
    lines.append(f"  Classification: {_color(report_dict['classification'], BOLD)}")
    lines.append(f"  Failure Rate: {report_dict['failure_rate'] * 100:.1f}%")

    if report_dict.get("peak_timing"):
        lines.append(f"  Peak Timing: {report_dict['peak_timing']}")

    lines.append("")
    lines.append(f"  {report_dict['pattern_description']}")

    return "\n".join(lines)


def format_contamination(report_dict: dict) -> str:
    """Format contamination tracker report for terminal output."""
    lines = []
    lines.append(_color(f"{SPREAD} Contamination Tracker — Flaky Test Epidemiology", BOLD))
    lines.append("")

    r0 = report_dict["overall_r0"]
    r0_color = GREEN if r0 < 1.0 else (YELLOW if r0 < 2.0 else RED)
    lines.append(f"  Overall R0: {r0_color}{r0:.3f}{RESET}")

    if report_dict.get("patient_zero"):
        lines.append(f"  Patient Zero: {_color(report_dict['patient_zero'], RED)}")
    else:
        lines.append(f"  Patient Zero: {_color('None identified', GREEN)}")

    lines.append("")

    flaky_nodes = [n for n in report_dict["nodes"] if n["is_flaky"]]
    if flaky_nodes:
        lines.append(_color("  Flaky Test Contamination Map:", BOLD))
        for node in flaky_nodes:
            r0_color = GREEN if node["r0"] < 1.0 else (YELLOW if node["r0"] < 2.0 else RED)
            lines.append(
                f"    {CROSS} {node['name']} "
                f"(R0={r0_color}{node['r0']:.3f}{RESET}, "
                f"targets={len(node['infected_targets'])})"
            )

    if report_dict.get("quarantine_plan"):
        lines.append("")
        lines.append(_color(f"  {QUARANTINE} Quarantine Plan:", BOLD))
        for test_id in report_dict["quarantine_plan"]:
            lines.append(f"    • {test_id}")

    if report_dict.get("inoculation_suggestions"):
        lines.append("")
        lines.append(_color(f"  {SUGGEST} Inoculation Suggestions:", BOLD))
        for suggestion in report_dict["inoculation_suggestions"]:
            lines.append(f"    • {suggestion}")

    return "\n".join(lines)


def format_feeding(report_dict: dict) -> str:
    """Format feeding schedule report for terminal output."""
    lines = []
    lines.append(_color(f"{CLOCK} Feeding Schedule — Test Maintenance Cadence", BOLD))
    lines.append("")

    adherence = report_dict["overall_adherence"]
    adh_color = GREEN if adherence >= 0.7 else (YELLOW if adherence >= 0.4 else RED)
    lines.append(f"  Overall Adherence: {adh_color}{adherence:.0%}{RESET}")
    lines.append("")

    if report_dict["modules"]:
        lines.append(_color("  Module Feeding Status:", BOLD))
        for m in report_dict["modules"]:
            status_symbol = {"healthy": CHECK, "hungry": WARNING, "starving": CROSS}.get(
                m["status"], "?"
            )
            status_color = {
                "healthy": GREEN,
                "hungry": YELLOW,
                "starving": RED,
            }.get(m["status"], RESET)
            lines.append(
                f"    {status_symbol} {m['module']}: "
                f"{status_color}{m['status']}{RESET} "
                f"(fed {m['last_fed_days_ago']:.0f}d ago, "
                f"{m['code_changes_since_feed']} code changes, "
                f"adherence: {m['feeding_adherence']:.0%})"
            )

    if report_dict.get("warnings"):
        lines.append("")
        for w in report_dict["warnings"]:
            lines.append(f"  {WARNING} {w}")

    return "\n".join(lines)


def format_build(report_dict: dict) -> str:
    """Format levain build report for terminal output."""
    lines = []
    lines.append(_color(f"{FLASK} Levain Build — Essential Test Subset", BOLD))
    lines.append("")

    confidence = report_dict["estimated_confidence"]
    conf_color = GREEN if confidence >= 0.9 else (YELLOW if confidence >= 0.7 else RED)
    lines.append(f"  Selected Tests: {report_dict['test_count']}")
    lines.append(f"  Estimated Confidence: {conf_color}{confidence:.0%}{RESET}")
    lines.append(f"  Proofing Time: {report_dict['proofing_time_seconds']:.1f}s")

    if report_dict.get("change_scope"):
        lines.append(f"  Change Scope: {report_dict['change_scope']}")

    lines.append("")
    lines.append(_color("  Selected Tests:", BOLD))
    for test_id in report_dict["selected_tests"]:
        lines.append(f"    {CHECK} {test_id}")

    return "\n".join(lines)


def format_thermal(report_dict: dict) -> str:
    """Format thermal profiler report for terminal output."""
    lines = []
    lines.append(_color(f"{THERMO} Thermal Profiler — Environment Sensitivity", BOLD))
    lines.append("")

    summary = report_dict.get("environment_summary", {})
    lines.append(
        f"  Thermophilic (sensitive): {summary.get('thermophilic', 'N/A')} | "
        f"Mesophilic (moderate): {summary.get('mesophilic', 'N/A')} | "
        f"Psychrophilic (robust): {summary.get('psychrophilic', 'N/A')}"
    )
    lines.append("")

    thermophilic = [
        p for p in report_dict["profiles"]
        if p["tolerance"] == "thermophilic"
    ]
    if thermophilic:
        lines.append(_color("  Thermophilic Tests (environment-sensitive):", BOLD))
        for p in thermophilic[:10]:
            factors = ", ".join(p["sensitivity_factors"]) if p["sensitivity_factors"] else "unknown"
            lines.append(f"    {CROSS} {p['name']} (factors: {factors})")
        lines.append("")

    if report_dict.get("climate_control_suggestions"):
        lines.append(_color(f"  {SUGGEST} Climate Control Suggestions:", BOLD))
        for suggestion in report_dict["climate_control_suggestions"]:
            lines.append(f"    • {suggestion}")

    return "\n".join(lines)


def format_health(report_dict: dict) -> str:
    """Format combined health report for terminal output."""
    lines = []
    lines.append(_color(f"{BREAD} Levain — Culture Health Report", BOLD))
    lines.append("=" * 50)
    lines.append("")

    health = report_dict["overall_health"]
    health_color = _score_color(health)
    lines.append(f"  Overall Health: {health_color}{health:.1f}/100{RESET}")
    lines.append(f"  {_bar(health)}")
    lines.append("")
    lines.append(f"  Diagnosis: {report_dict['diagnosis']}")
    lines.append("")
    lines.append("-" * 50)

    # Sub-reports
    if "hooch" in report_dict:
        lines.append("")
        lines.extend(format_hooch(report_dict["hooch"]).split("\n"))

    if "rise" in report_dict:
        lines.append("")
        lines.extend(format_rise(report_dict["rise"]).split("\n"))

    if "contamination" in report_dict:
        lines.append("")
        lines.extend(format_contamination(report_dict["contamination"]).split("\n"))

    if "feeding" in report_dict:
        lines.append("")
        lines.extend(format_feeding(report_dict["feeding"]).split("\n"))

    return "\n".join(lines)


def output_report(report_dict: dict, report_type: str, json_output: bool = False) -> None:
    """Output a report either as formatted text or JSON.

    Args:
        report_dict: Report data as dictionary.
        report_type: Type of report (health, hooch, rise, contamination, feeding, build, thermal).
        json_output: If True, output as JSON.
    """
    if json_output:
        print(json.dumps(report_dict, indent=2))
        return

    formatters = {
        "health": format_health,
        "hooch": format_hooch,
        "rise": format_rise,
        "contamination": format_contamination,
        "feeding": format_feeding,
        "build": format_build,
        "thermal": format_thermal,
    }

    formatter = formatters.get(report_type)
    if formatter:
        print(formatter(report_dict))
    else:
        print(json.dumps(report_dict, indent=2))
