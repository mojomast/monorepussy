"""Chromatogram renderer — ASCII chart and JSON output."""

from __future__ import annotations

import json
from chromato.models import (
    ChromatogramResult,
    Coelution,
    EntanglementKind,
    Peak,
    PeakShape,
)


def render_chromatogram(result: ChromatogramResult) -> str:
    """Render a chromatogram as a Unicode/ASCII art display.

    Args:
        result: The chromatogram result to render.

    Returns:
        Formatted string with the chromatogram display.
    """
    lines: list[str] = []

    # Header
    title = f"CHROMATOGRAM: {result.source} ({result.solvent.value} solvent)"
    width = max(61, len(title) + 4)
    border = "─" * (width - 2)

    lines.append(f"╭{border}╮")
    lines.append(f"│  {title:<{width - 4}}  │")
    lines.append(f"├{border}┤")
    lines.append(f"│{'':^{width - 2}}│")

    # Column headers
    rt_col = "RT"
    dep_col = "Dependency"
    shape_col = "Shape"
    area_col = "Area"
    diag_col = "Diagnosis"

    header = f"  {rt_col:<5} {dep_col:<22} {shape_col:<10} {area_col:<6} {diag_col:<14}"
    divider = f"  {'───':<5} {'──────────────────────':<22} {'──────────':<10} {'──────':<6} {'──────────────':<14}"

    lines.append(f"│{header:<{width - 2}}│")
    lines.append(f"│{divider:<{width - 2}}│")

    # Peaks
    for peak in result.peaks:
        shape_icon = _shape_icon(peak.shape)
        area_bar = _area_bar(peak.area)
        diagnosis = _diagnosis(peak)

        # Check for co-elution
        coelution_flag = ""
        for ce in result.coelutions:
            if ce.dep_a.name == peak.dep.name or ce.dep_b.name == peak.dep.name:
                coelution_flag = " ⚡"
                break

        row = f"  {peak.retention_time:<5.1f} {peak.dep.name:<22} {shape_icon:<10} {area_bar:<6} {diagnosis:<14}{coelution_flag}"
        # Truncate to fit
        if len(row) > width - 2:
            row = row[:width - 5] + "..."
        lines.append(f"│{row:<{width - 2}}│")

    lines.append(f"│{'':^{width - 2}}│")

    # Co-elution warnings
    for ce in result.coelutions:
        kind_str = ce.kind.value
        warn = f"  ⚠ CO-ELUTION: {ce.dep_a.name} + {ce.dep_b.name} (overlap={ce.overlap:.2f}, {kind_str})"
        if len(warn) > width - 2:
            warn = warn[:width - 5] + "..."
        lines.append(f"│{warn:<{width - 2}}│")

    # Peak diagnosis warnings
    for peak in result.peaks:
        if peak.shape in (PeakShape.WIDE_SHORT, PeakShape.TAILING, PeakShape.SHOULDER):
            concerns = peak.dep.concerns
            warn = f"  ⚠ PEAK DIAGNOSIS: {peak.dep.name} is {_shape_label(peak.shape)} ({concerns} concerns)"
            if len(warn) > width - 2:
                warn = warn[:width - 5] + "..."
            lines.append(f"│{warn:<{width - 2}}│")

    lines.append(f"╰{border}╯")

    return "\n".join(lines)


def _shape_icon(shape: PeakShape) -> str:
    """Return a visual representation for the peak shape."""
    icons = {
        PeakShape.NARROW_TALL: "████",
        PeakShape.WIDE_SHORT: "██░░░░",
        PeakShape.SHOULDER: "██▓░░",
        PeakShape.TAILING: "██░░▓",
        PeakShape.SYMMETRIC: "████",
    }
    return icons.get(shape, "████")


def _area_bar(area: float) -> str:
    """Return a bar representation for peak area."""
    bars = int(area * 10)
    bars = max(1, min(10, bars))
    return "█" * bars


def _shape_label(shape: PeakShape) -> str:
    """Return a human-readable label for the peak shape."""
    labels = {
        PeakShape.NARROW_TALL: "focused",
        PeakShape.WIDE_SHORT: "wide",
        PeakShape.SHOULDER: "shoulder",
        PeakShape.TAILING: "tailing",
        PeakShape.SYMMETRIC: "normal",
    }
    return labels.get(shape, "normal")


def _diagnosis(peak: Peak) -> str:
    """Return a diagnosis string for a peak."""
    if peak.shape == PeakShape.NARROW_TALL:
        return "✓ focused"
    elif peak.shape == PeakShape.WIDE_SHORT:
        return "⚠ wide"
    elif peak.shape == PeakShape.SHOULDER:
        return "↗ shoulder"
    elif peak.shape == PeakShape.TAILING:
        return "⚠ tailing"
    elif peak.shape == PeakShape.SYMMETRIC:
        return "✓ normal"
    return "✓ normal"


def render_json(result: ChromatogramResult) -> str:
    """Render chromatogram result as JSON.

    Args:
        result: The chromatogram result to render.

    Returns:
        JSON string representation.
    """
    data = {
        "source": result.source,
        "solvent": result.solvent.value,
        "timestamp": result.timestamp.isoformat(),
        "peaks": [
            {
                "name": peak.dep.name,
                "version": peak.dep.version,
                "retention_time": peak.retention_time,
                "area": peak.area,
                "width": peak.width,
                "height": peak.height,
                "shape": peak.shape.value,
                "license": peak.dep.license,
                "is_dev": peak.dep.is_dev,
                "diagnosis": _diagnosis(peak),
            }
            for peak in result.peaks
        ],
        "coelutions": [
            {
                "dep_a": ce.dep_a.name,
                "dep_b": ce.dep_b.name,
                "overlap": ce.overlap,
                "kind": ce.kind.value,
            }
            for ce in result.coelutions
        ],
        "summary": {
            "total_dependencies": len(result.peaks),
            "total_coelutions": len(result.coelutions),
            "max_risk_score": max(
                (p.retention_time for p in result.peaks), default=0.0
            ),
            "health_ratio": _compute_health_ratio(result.peaks),
        },
    }
    return json.dumps(data, indent=2)


def _compute_health_ratio(peaks: list[Peak]) -> float:
    """Compute the ratio of healthy to unhealthy peaks."""
    if not peaks:
        return 1.0
    healthy = sum(
        1 for p in peaks
        if p.shape in (PeakShape.NARROW_TALL, PeakShape.SYMMETRIC)
    )
    return round(healthy / len(peaks), 2)


def render_diff(
    result_a: ChromatogramResult,
    result_b: ChromatogramResult,
) -> str:
    """Render a differential chromatogram comparing two results.

    Args:
        result_a: The original chromatogram.
        result_b: The new chromatogram.

    Returns:
        Formatted diff string.
    """
    lines: list[str] = []

    lines.append("╭── DIFFERENTIAL CHROMATOGRAM ──────────────────────╮")
    lines.append(f"│  A: {result_a.source:<45}  │")
    lines.append(f"│  B: {result_b.source:<45}  │")
    lines.append("├───────────────────────────────────────────────────┤")

    # Build lookup for quick comparison
    peaks_a = {p.dep.name: p for p in result_a.peaks}
    peaks_b = {p.dep.name: p for p in result_b.peaks}

    all_names = sorted(set(peaks_a.keys()) | set(peaks_b.keys()))

    for name in all_names:
        in_a = name in peaks_a
        in_b = name in peaks_b

        if in_a and in_b:
            pa = peaks_a[name]
            pb = peaks_b[name]
            rt_diff = pb.retention_time - pa.retention_time
            direction = "↑" if rt_diff > 0 else "↓" if rt_diff < 0 else "="
            line = f"  {name:<20} RT: {pa.retention_time:.1f}→{pb.retention_time:.1f} ({direction}{abs(rt_diff):.1f})"
        elif in_b:
            pb = peaks_b[name]
            line = f"  + {name:<18} RT: {pb.retention_time:.1f} (ADDED)"
        else:
            pa = peaks_a[name]
            line = f"  - {name:<18} RT: {pa.retention_time:.1f} (REMOVED)"

        lines.append(f"│{line:<50}│")

    # Co-elution changes
    coelutions_a = {(c.dep_a.name, c.dep_b.name) for c in result_a.coelutions}
    coelutions_b = {(c.dep_a.name, c.dep_b.name) for c in result_b.coelutions}

    new_coelutions = coelutions_b - coelutions_a
    resolved_coelutions = coelutions_a - coelutions_b

    for pair in new_coelutions:
        line = f"  ⚠ NEW CO-ELUTION: {pair[0]} + {pair[1]}"
        lines.append(f"│{line:<50}│")

    for pair in resolved_coelutions:
        line = f"  ✓ RESOLVED: {pair[0]} + {pair[1]}"
        lines.append(f"│{line:<50}│")

    lines.append("╰───────────────────────────────────────────────────╯")
    return "\n".join(lines)
