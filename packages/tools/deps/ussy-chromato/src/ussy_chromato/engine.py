"""Chromato Engine — orchestrates the full separation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ussy_chromato.coelution import detect_coelution
from ussy_chromato.models import ChromatogramResult, Solvent
from ussy_chromato.peak import build_peaks
from ussy_chromato.retention import compute_all_retention_times
from ussy_chromato.parser import parse_dependency_file


def run_scan(
    source: str,
    solvent: Solvent = Solvent.COUPLING,
    coelution_threshold: float = 0.3,
) -> ChromatogramResult:
    """Run a full chromatographic scan on a dependency file or directory.

    Args:
        source: Path to dependency file or directory.
        solvent: Analysis mode.
        coelution_threshold: Overlap threshold for co-elution detection.

    Returns:
        ChromatogramResult with peaks and co-elutions.
    """
    # 1. Parse dependency file(s)
    graph = parse_dependency_file(source)

    # 2. Compute retention times
    retention_times = compute_all_retention_times(graph, solvent)

    # 3. Build peaks
    peaks = build_peaks(graph, retention_times, solvent.value)

    # 4. Detect co-elution
    coelutions = detect_coelution(peaks, graph, coelution_threshold)

    return ChromatogramResult(
        source=source,
        solvent=solvent,
        peaks=peaks,
        coelutions=coelutions,
        timestamp=datetime.now(timezone.utc),
    )


def run_diff(
    source_a: str,
    source_b: str,
    solvent: Solvent = Solvent.COUPLING,
    coelution_threshold: float = 0.3,
) -> tuple[ChromatogramResult, ChromatogramResult]:
    """Run a differential chromatogram comparing two dependency files.

    Args:
        source_a: Path to the original dependency file.
        source_b: Path to the new dependency file.
        solvent: Analysis mode.
        coelution_threshold: Overlap threshold for co-elution detection.

    Returns:
        Tuple of (original, new) ChromatogramResults.
    """
    result_a = run_scan(source_a, solvent, coelution_threshold)
    result_b = run_scan(source_b, solvent, coelution_threshold)
    return result_a, result_b


def compute_max_risk(result: ChromatogramResult) -> float:
    """Compute the maximum risk score from a chromatogram result.

    Returns:
        The maximum retention time across all peaks (0.0 if no peaks).
    """
    if not result.peaks:
        return 0.0
    return max(p.retention_time for p in result.peaks)
