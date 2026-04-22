"""Peak shape analysis — diagnose dependency health from peak shape."""

from __future__ import annotations

from chromato.models import Dependency, DependencyGraph, Peak, PeakShape


def count_concerns(dep: Dependency) -> int:
    """Count how many distinct purposes/concerns a dependency has.

    Uses the 'concerns' field if set, otherwise heuristics from name.
    """
    if dep.concerns > 1:
        return dep.concerns
    # Heuristic: multi-purpose libraries often have compound names
    name_lower = dep.name.lower()
    # Common multi-concern indicators
    multi_indicators = [
        "util", "tool", "helper", "common", "misc", "all", "full",
        "extra", "plus", "meta", "bundle", "kit", "swiss",
    ]
    count = 1
    for indicator in multi_indicators:
        if indicator in name_lower:
            count += 1
            break
    return count


def analyze_peak(dep: Dependency, graph: DependencyGraph) -> PeakShape:
    """Diagnose dependency health from peak shape.

    - NARROW_TALL: Focused + popular (healthy)
    - WIDE_SHORT: Bloated: does too much
    - SHOULDER: Transition: version split
    - TAILING: Drag: backward compat burden
    - SYMMETRIC: Normal
    """
    concerns = count_concerns(dep)
    dependents_count = graph.dependent_count(dep)

    if concerns == 1 and dependents_count > 5:
        return PeakShape.NARROW_TALL
    elif concerns > 3:
        return PeakShape.WIDE_SHORT
    elif dep.has_major_version_gap:
        return PeakShape.SHOULDER
    elif dep.has_deprecated_apis:
        return PeakShape.TAILING
    return PeakShape.SYMMETRIC


def compute_peak_area(dep: Dependency, graph: DependencyGraph) -> float:
    """Compute peak area = dependency "mass" (dependents × risk weight).

    Area represents the impact/importance of the dependency.
    """
    dependents = graph.dependent_count(dep)
    risk_weight = 1.0 + 0.1 * dep.advisory_count
    # Normalize to 0-1 range
    area = min(1.0, (dependents * risk_weight) / 20.0)
    return round(area, 2)


def compute_peak_width(dep: Dependency) -> float:
    """Compute peak width = dependency "purity".

    Narrow = single-purpose, Wide = multi-concern.
    """
    concerns = count_concerns(dep)
    # 1 concern → width 0.2, 5+ concerns → width 1.0
    width = min(1.0, 0.2 * concerns)
    return round(width, 2)


def build_peaks(
    graph: DependencyGraph,
    retention_times: dict[str, float],
    solvent_name: str = "coupling",
) -> list[Peak]:
    """Build Peak objects for all dependencies in the graph.

    Args:
        graph: The dependency graph.
        retention_times: Pre-computed retention times per dependency name.
        solvent_name: Name of the solvent used (for display).

    Returns:
        List of Peak objects sorted by retention time.
    """
    peaks: list[Peak] = []
    for dep in graph.dependencies:
        rt = retention_times.get(dep.name, 0.0)
        area = compute_peak_area(dep, graph)
        width = compute_peak_width(dep)
        shape = analyze_peak(dep, graph)
        height = area / max(width, 0.1)  # Gaussian-like: height = area/width

        peak = Peak(
            dep=dep,
            retention_time=round(rt, 2),
            area=area,
            width=width,
            height=round(height, 2),
            shape=shape,
        )
        peaks.append(peak)

    # Sort by retention time
    peaks.sort(key=lambda p: p.retention_time)
    return peaks
