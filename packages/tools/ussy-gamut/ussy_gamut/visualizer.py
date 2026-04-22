"""ASCII CIE-chromaticity-style gamut diagram visualizer.

Renders pipeline gamut boundaries as overlapping 2D diagrams using
text characters instead of pixels. Each stage is a region; overlapping
areas are safe; protruding areas are clipping zones.
"""

from __future__ import annotations

import math
from typing import Any

from ussy_gamut.models import (
    BoundaryReport,
    ClippingRisk,
    ClippingResult,
    PipelineDAG,
    StageProfile,
)


# Character palette for gamut regions
_CHAR_SAFE = "█"       # In-gamut (safe)
_CHAR_SOURCE = "▓"     # Source-only (clipping zone)
_CHAR_DEST = "▒"       # Dest-only (safe, but wasted capacity)
_CHAR_OVERLAP = "░"    # Overlap region
_CHAR_EMPTY = " "      # Outside both gamuts
_CHAR_BORDER = "·"     # Border marker
_CHAR_CLIPPING = "✕"   # Clipping marker

# Risk color indicators (for terminals that support it)
_RISK_MARKERS = {
    ClippingRisk.NONE: " ",
    ClippingRisk.LOW: "·",
    ClippingRisk.MEDIUM: "○",
    ClippingRisk.HIGH: "●",
    ClippingRisk.CRITICAL: "✕",
}


def render_gamut_diagram(
    report: BoundaryReport,
    width: int = 60,
    height: int = 20,
) -> str:
    """Render a CIE-style gamut diagram for a boundary report.

    The diagram shows two overlapping gamut regions:
    - Source gamut (larger region)
    - Destination gamut (smaller region, inside or overlapping)

    Protruding parts of the source gamut represent clipping zones.
    """
    lines: list[str] = []

    # Header
    lines.append(f"Gamut Diagram: {report.source_stage} → {report.dest_stage}")
    lines.append("")

    # Compute gamut regions
    # Use delta_e values to determine gamut shape per field
    clipping_results = report.get_clipping_results()

    if not clipping_results:
        lines.append("  ╔══════════════════════════════════════════╗")
        lines.append("  ║  All fields in-gamut — no clipping       ║")
        lines.append("  ╚══════════════════════════════════════════╝")
        lines.append("")
        return "\n".join(lines)

    # Build a 2D grid
    grid = [[_CHAR_EMPTY for _ in range(width)] for _ in range(height)]

    # Compute field positions along x-axis
    field_count = len(clipping_results)
    if field_count == 0:
        return "\n".join(lines)

    # Each field gets a column range
    cols_per_field = max(1, width // max(field_count, 1))

    for idx, cr in enumerate(clipping_results):
        col_start = idx * cols_per_field
        col_end = min(col_start + cols_per_field, width)

        # Source gamut height (proportional to delta_e)
        # Full height = source gamut; inner region = dest gamut
        src_rows = max(2, int((1.0 - cr.delta_e / 100.0) * height))
        dst_rows = max(1, int((1.0 - cr.delta_e / 100.0) * height * 0.8))

        # Total rows to draw: source height based on full range
        src_height = height - 1
        dst_height = max(1, src_height - int(cr.delta_e / 100.0 * height * 0.5))

        center_y = height // 2

        # Draw source gamut
        for row in range(max(0, center_y - src_height // 2), min(height, center_y + src_height // 2 + 1)):
            for col in range(col_start, col_end):
                if col < width:
                    grid[row][col] = _CHAR_SOURCE

        # Draw destination gamut (overlap)
        for row in range(max(0, center_y - dst_height // 2), min(height, center_y + dst_height // 2 + 1)):
            for col in range(col_start + 1, min(col_end - 1, width)):
                if col < width and row < height:
                    if grid[row][col] == _CHAR_SOURCE:
                        grid[row][col] = _CHAR_OVERLAP  # Overlap = safe
                    else:
                        grid[row][col] = _CHAR_DEST

        # Mark clipping zone
        if cr.delta_e > 0:
            clip_row = max(0, center_y - src_height // 2)
            clip_col = min(col_start + cols_per_field // 2, width - 1)
            if clip_row < height and clip_col < width:
                grid[clip_row][clip_col] = _CHAR_CLIPPING

    # Render grid
    lines.append(f"  {'─' * width}")
    for row in grid:
        lines.append(f"  {''.join(row)}")
    lines.append(f"  {'─' * width}")

    # Legend
    lines.append("")
    lines.append("  Legend:")
    lines.append(f"    {_CHAR_SOURCE} Source gamut (clipping zone)")
    lines.append(f"    {_CHAR_DEST}  Destination gamut")
    lines.append(f"    {_CHAR_OVERLAP} Overlap (safe)")
    lines.append(f"    {_CHAR_CLIPPING} Clipping boundary")
    lines.append("")

    # Field labels
    lines.append("  Fields:")
    for idx, cr in enumerate(clipping_results):
        marker = _RISK_MARKERS.get(cr.risk, "?")
        lines.append(
            f"    [{idx + 1}] {cr.field_name:30s} "
            f"ΔE={cr.delta_e:6.2f}  risk={cr.risk.value:8s} "
            f"intent={cr.rendering_intent.value:22s} {marker}"
        )

    return "\n".join(lines)


def render_pipeline_overview(
    reports: list[BoundaryReport],
    dag: PipelineDAG,
) -> str:
    """Render a text-based pipeline overview showing all boundaries."""
    lines: list[str] = []

    lines.append(f"Pipeline: {dag.name}")
    lines.append("=" * 70)
    lines.append("")

    # Stage chain
    stage_names = list(dag.stages.keys())
    if stage_names:
        chain = " → ".join(stage_names)
        lines.append(f"  Stages: {chain}")
        lines.append("")

    # Summary per boundary
    for report in reports:
        lines.append(f"  Boundary: {report.source_stage} → {report.dest_stage}")
        lines.append(f"    Fields analyzed : {len(report.results)}")
        lines.append(f"    Clipping fields : {report.clipping_count}")
        lines.append(f"    Critical fields : {report.critical_count}")
        lines.append(f"    Max ΔE          : {report.max_delta_e:.2f}")
        lines.append("")

        # Detail on clipping fields
        for cr in report.get_clipping_results():
            lines.append(f"    ⚠ {cr.field_name}")
            lines.append(f"      {cr.source_gamut.system}:{cr.source_gamut.type_name} "
                         f"→ {cr.dest_gamut.system}:{cr.dest_gamut.type_name}")
            lines.append(f"      ΔE={cr.delta_e:.2f}  risk={cr.risk.value}  "
                         f"intent={cr.rendering_intent.value}")
            for ex in cr.clipped_examples[:3]:
                lines.append(f"      · {ex}")
            lines.append("")

    return "\n".join(lines)


def render_field_detail(cr: ClippingResult) -> str:
    """Render detailed information about a single field clipping result."""
    lines: list[str] = []

    lines.append(f"Field: {cr.field_name}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"  Source: {cr.source_gamut.system}:{cr.source_gamut.type_name}")
    lines.append(f"    field_type   = {cr.source_gamut.field_type.value}")
    lines.append(f"    min_value    = {cr.source_gamut.min_value}")
    lines.append(f"    max_value    = {cr.source_gamut.max_value}")
    lines.append(f"    precision    = {cr.source_gamut.precision}")
    lines.append(f"    scale        = {cr.source_gamut.scale}")
    lines.append(f"    timezone_aware = {cr.source_gamut.timezone_aware}")
    lines.append(f"    tz_precision = {cr.source_gamut.tz_precision}")
    lines.append(f"    charset      = {cr.source_gamut.charset}")
    lines.append(f"    max_length   = {cr.source_gamut.max_length}")
    lines.append(f"    nullable     = {cr.source_gamut.nullable}")
    lines.append("")
    lines.append(f"  Destination: {cr.dest_gamut.system}:{cr.dest_gamut.type_name}")
    lines.append(f"    field_type   = {cr.dest_gamut.field_type.value}")
    lines.append(f"    min_value    = {cr.dest_gamut.min_value}")
    lines.append(f"    max_value    = {cr.dest_gamut.max_value}")
    lines.append(f"    precision    = {cr.dest_gamut.precision}")
    lines.append(f"    scale        = {cr.dest_gamut.scale}")
    lines.append(f"    timezone_aware = {cr.dest_gamut.timezone_aware}")
    lines.append(f"    tz_precision = {cr.dest_gamut.tz_precision}")
    lines.append(f"    charset      = {cr.dest_gamut.charset}")
    lines.append(f"    max_length   = {cr.dest_gamut.max_length}")
    lines.append(f"    nullable     = {cr.dest_gamut.nullable}")
    lines.append("")
    lines.append(f"  Analysis:")
    lines.append(f"    ΔE             = {cr.delta_e:.4f}")
    lines.append(f"    risk           = {cr.risk.value}")
    lines.append(f"    rendering_intent = {cr.rendering_intent.value}")
    lines.append(f"    is_clipping    = {cr.is_clipping}")
    lines.append("")

    if cr.clipped_examples:
        lines.append("  Clipping Examples:")
        for ex in cr.clipped_examples:
            lines.append(f"    • {ex}")
        lines.append("")

    if cr.notes:
        lines.append("  Notes:")
        for n in cr.notes:
            lines.append(f"    · {n}")
        lines.append("")

    return "\n".join(lines)


def render_boundary_comparison(
    source: StageProfile,
    dest: StageProfile,
    report: BoundaryReport,
) -> str:
    """Render a side-by-side comparison of two stage gamuts."""
    lines: list[str] = []

    lines.append(f"Stage Comparison: {source.name} → {dest.name}")
    lines.append("")

    # Field-by-field table
    src_fields = {f.name: f for f in source.fields}
    dst_fields = {f.name: f for f in dest.fields}
    all_names = sorted(set(src_fields.keys()) | set(dst_fields.keys()))

    # Table header
    name_w = 20
    type_w = 18
    lines.append(f"  {'Field':<{name_w}} {'Source Type':<{type_w}} {'Dest Type':<{type_w}} {'ΔE':>6} {'Risk':>8} {'Intent':>12}")
    lines.append(f"  {'─' * name_w} {'─' * type_w} {'─' * type_w} {'─' * 6} {'─' * 8} {'─' * 12}")

    result_map = {r.field_name: r for r in report.results}

    for name in all_names:
        src_f = src_fields.get(name)
        dst_f = dst_fields.get(name)
        src_t = src_f.gamut.type_name if src_f else "<missing>"
        dst_t = dst_f.gamut.type_name if dst_f else "<missing>"
        cr = result_map.get(name)

        if cr:
            de_str = f"{cr.delta_e:.2f}"
            risk_str = cr.risk.value
            intent_str = cr.rendering_intent.value[:12]
        else:
            de_str = "-"
            risk_str = "-"
            intent_str = "-"

        lines.append(f"  {name:<{name_w}} {src_t:<{type_w}} {dst_t:<{type_w}} {de_str:>6} {risk_str:>8} {intent_str:>12}")

    lines.append("")
    return "\n".join(lines)
