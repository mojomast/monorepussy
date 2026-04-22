"""ASCII geological rendering — terminal-based stratigraphic column display."""

from __future__ import annotations

from typing import List

from ussy_stratax.models import (
    BedrockReport,
    DiffResult,
    ErosionReport,
    FaultLine,
    ScanResult,
    StratigraphicColumn,
)

# Unicode block characters for geological rendering
BLOCK_FULL = "\u2588"  # █
BLOCK_7_8 = "\u2587"
BLOCK_3_4 = "\u2586"
BLOCK_5_8 = "\u2585"
BLOCK_HALF = "\u2584"
BLOCK_3_8 = "\u2583"
BLOCK_1_4 = "\u2582"
BLOCK_1_8 = "\u2581"
BLOCK_EMPTY = "\u2591"  # ░

TIER_SYMBOLS = {
    "bedrock": BLOCK_FULL,
    "stable": BLOCK_3_4,
    "hazard": BLOCK_HALF,
    "quicksand": BLOCK_1_4,
    "deprecated": BLOCK_1_8,
}

TIER_COLORS = {
    "bedrock": "\033[32m",     # Green
    "stable": "\033[36m",      # Cyan
    "hazard": "\033[33m",      # Yellow
    "quicksand": "\033[31m",   # Red
    "deprecated": "\033[90m",  # Gray
}
RESET_COLOR = "\033[0m"

HAZARD_ICONS = {
    "dormant": "✓",
    "minor": "⚡",
    "moderate": "⚠",
    "major": "🔥",
    "catastrophic": "💀",
}


class ASCIIRenderer:
    """Render stratigraphic data as ASCII geological formations."""

    def __init__(self, use_color: bool = True, width: int = 50):
        self.use_color = use_color
        self.width = width

    def render_column(self, column: StratigraphicColumn) -> str:
        """Render a stratigraphic column as an ASCII display."""
        lines = []

        # Header
        header = f" {column.package} stratigraphic column "
        box_width = self.width + 20
        lines.append("┌" + "─" * (box_width - 2) + "┐")
        lines.append("│" + header.center(box_width - 2) + "│")
        lines.append("├" + "─" * (box_width - 2) + "┤")

        # Each function as a geological layer
        for report in column.bedrock_reports:
            bar_len = int(report.bedrock_score / 100 * self.width)
            empty_len = self.width - bar_len

            symbol = TIER_SYMBOLS.get(report.stability_tier, BLOCK_HALF)

            # Build the bar
            bar = symbol * bar_len + BLOCK_EMPTY * empty_len

            # Apply color
            if self.use_color:
                color = TIER_COLORS.get(report.stability_tier, "")
                bar = f"{color}{bar}{RESET_COLOR}"

            tier_label = report.stability_tier
            line = f"│ {bar} {report.function} ({tier_label}: {report.bedrock_score:.0f})"
            # Pad to box width
            padding = box_width - len(line) - 1
            if padding > 0:
                line += " " * padding
            line += "│"
            lines.append(line)

        # Footer
        lines.append("├" + "─" * (box_width - 2) + "┤")

        # Summary
        fault_count = len(column.fault_lines)
        erosion_count = sum(1 for e in column.erosion_reports if e.is_eroding)
        quicksand = sum(
            1 for r in column.bedrock_reports
            if r.stability_tier in ("quicksand", "deprecated")
        )

        if fault_count:
            icon = "⚠️" if self.use_color else "[!]"
            lines.append(
                f"│ {icon} {fault_count} fault line(s) detected"
                + " " * (box_width - len(f"│ {icon} {fault_count} fault line(s) detected") - 2)
                + "│"
            )
        if erosion_count:
            icon = "📉" if self.use_color else "[~]"
            lines.append(
                f"│ {icon} {erosion_count} erosion zone(s)"
                + " " * (box_width - len(f"│ {icon} {erosion_count} erosion zone(s)") - 2)
                + "│"
            )
        if quicksand:
            icon = "💀" if self.use_color else "[X]"
            lines.append(
                f"│ {icon} {quicksand} quicksand zone(s)"
                + " " * (box_width - len(f"│ {icon} {quicksand} quicksand zone(s)") - 2)
                + "│"
            )
        if not fault_count and not erosion_count and not quicksand:
            lines.append(
                "│ ✓ No hazards detected"
                + " " * (box_width - len("│ ✓ No hazards detected") - 2)
                + "│"
            )

        lines.append("└" + "─" * (box_width - 2) + "┘")

        # Strip ANSI codes for length calculations — use plain output
        return "\n".join(self._fix_padding(lines))

    def render_scan_result(self, result: ScanResult) -> str:
        """Render a scan result with hazard details."""
        lines = []

        lines.append(f"Strata scan: {result.lockfile}")
        lines.append(f"  Packages scanned: {result.packages_scanned}")
        lines.append("")

        if result.fault_lines:
            lines.append(f"⚠️  {len(result.fault_lines)} FAULT LINE(S) detected")
            for fl in result.fault_lines:
                lines.append(f"  {fl.package} — {fl.description}")
            lines.append("")

        if result.quicksand_zones:
            lines.append(f"💀  {len(result.quicksand_zones)} QUICKSAND ZONE(S)")
            for qz in result.quicksand_zones:
                lines.append(
                    f"  {qz.package}.{qz.function} — "
                    f"stability: {qz.stability_tier} (score: {qz.bedrock_score:.0f})"
                )
            lines.append("")

        if result.erosion_warnings:
            lines.append(f"📉  {len(result.erosion_warnings)} EROSION WARNING(S)")
            for ew in result.erosion_warnings:
                lines.append(
                    f"  {ew.package}.{ew.function} — "
                    f"declining: {ew.initial_pass_rate:.0%} → {ew.current_pass_rate:.0%}"
                )
            lines.append("")

        if not result.has_hazards:
            lines.append("✓ No seismic hazards detected")

        return "\n".join(lines)

    def render_diff_result(self, diff: DiffResult) -> str:
        """Render a version diff result."""
        lines = []

        lines.append(
            f"Strata diff: {diff.package}@{diff.version_a} → {diff.package}@{diff.version_b}"
        )
        lines.append("")

        if diff.behavioral_quakes:
            lines.append(f"  {len(diff.behavioral_quakes)} behavioral quake(s) detected")
            for quake in diff.behavioral_quakes:
                lines.append(f"    - {quake.get('description', 'Unknown change')}")
        else:
            lines.append("  No behavioral changes detected")

        if diff.new_behaviors:
            lines.append(f"  {len(diff.new_behaviors)} new behavior(s)")
            for nb in diff.new_behaviors:
                lines.append(f"    + {nb}")

        if diff.removed_behaviors:
            lines.append(f"  {len(diff.removed_behaviors)} removed behavior(s)")
            for rb in diff.removed_behaviors:
                lines.append(f"    - {rb}")

        if not diff.has_quakes and not diff.new_behaviors and not diff.removed_behaviors:
            lines.append(
                f"  {diff.unchanged_count} probe(s) unchanged — these versions are behaviorally compatible"
            )

        return "\n".join(lines)

    def _fix_padding(self, lines: List[str]) -> List[str]:
        """Fix line padding to ensure box alignment, ignoring ANSI escape codes."""
        import re

        fixed = []
        # Determine the target width from the top border
        target_width = len(lines[0]) if lines else 70

        for line in lines:
            # Strip ANSI escape codes to measure visible width
            visible = re.sub(r"\033\[[0-9;]*m", "", line)
            visible_len = len(visible)

            if visible_len < target_width:
                # Add padding before the closing │
                if line.rstrip().endswith("│"):
                    # Remove trailing │, add padding, re-add │
                    line = line.rstrip()[:-1]
                    line += " " * (target_width - visible_len - 1) + "│"

            fixed.append(line)

        return fixed
