"""Co-elution detection — find overlapping peaks = entangled dependencies."""

from __future__ import annotations

from chromato.models import (
    Coelution,
    DependencyGraph,
    EntanglementKind,
    Peak,
)


def peak_overlap(peak_a: Peak, peak_b: Peak) -> float:
    """Compute overlap fraction between two peaks.

    Uses Gaussian-like overlap based on retention times and widths.

    Returns:
        Overlap fraction (0.0 = no overlap, 1.0 = complete overlap).
    """
    # Distance between peak centers
    dist = abs(peak_a.retention_time - peak_b.retention_time)

    # Combined width (use sum of half-widths as the interaction range)
    sigma_a = peak_a.width / 2.0
    sigma_b = peak_b.width / 2.0
    combined_sigma = max(sigma_a + sigma_b, 0.01)

    # Gaussian-like overlap
    if combined_sigma == 0:
        return 0.0

    overlap = max(0.0, 1.0 - dist / combined_sigma)
    return round(overlap, 3)


def classify_entanglement(
    dep_a_name: str,
    dep_b_name: str,
    graph: DependencyGraph,
) -> EntanglementKind:
    """Classify the type of entanglement between two dependencies.

    Args:
        dep_a_name: Name of first dependency.
        dep_b_name: Name of second dependency.
        graph: The dependency graph.

    Returns:
        The type of entanglement detected.
    """
    if graph.has_circular(dep_a_name, dep_b_name):
        return EntanglementKind.CIRCULAR

    # Check if they have a direct mutual edge
    has_ab = any(frm == dep_a_name and to == dep_b_name for frm, to in graph.edges)
    has_ba = any(frm == dep_b_name and to == dep_a_name for frm, to in graph.edges)

    if has_ab and has_ba:
        return EntanglementKind.CIRCULAR

    # Check for version conflict: both depend on a common dep with different versions
    # (simplified heuristic: if both appear as dependents of the same node)
    deps_of_a = {to for frm, to in graph.edges if frm == dep_a_name}
    deps_of_b = {to for frm, to in graph.edges if frm == dep_b_name}
    common = deps_of_a & deps_of_b
    if common:
        return EntanglementKind.CONFLICT

    if has_ab or has_ba:
        return EntanglementKind.MUTUAL

    return EntanglementKind.MUTUAL


def detect_coelution(
    peaks: list[Peak],
    graph: DependencyGraph,
    threshold: float = 0.3,
) -> list[Coelution]:
    """Find overlapping peaks = entangled dependencies.

    Args:
        peaks: List of computed peaks.
        graph: The dependency graph.
        threshold: Minimum overlap fraction to report (default 0.3 = 30%).

    Returns:
        List of Coelution objects representing entangled dependencies.
    """
    coelutions: list[Coelution] = []
    for i, peak_a in enumerate(peaks):
        for peak_b in peaks[i + 1:]:
            overlap = peak_overlap(peak_a, peak_b)
            if overlap > threshold:
                entanglement = classify_entanglement(
                    peak_a.dep.name,
                    peak_b.dep.name,
                    graph,
                )
                coelutions.append(Coelution(
                    dep_a=peak_a.dep,
                    dep_b=peak_b.dep,
                    overlap=overlap,
                    kind=entanglement,
                ))
    return coelutions
