"""Full forensic investigation — orchestrates all analysis modules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ussy_coroner.models import (
    CustodyChain,
    CustodyComparison,
    Investigation,
    PipelineRun,
    SpatterReconstruction,
    TraceTransferResult,
)
from ussy_coroner.custody import analyze_custody
from ussy_coroner.luminol import analyze_luminol
from ussy_coroner.spatter import analyze_spatter
from ussy_coroner.striation import analyze_striations
from ussy_coroner.traces import analyze_traces


def investigate(
    run: PipelineRun,
    compare_runs: list[PipelineRun] | None = None,
    bidirectional: bool = True,
) -> Investigation:
    """Perform a full forensic investigation of a pipeline run.

    Orchestrates all analysis modules:
    1. Trace Evidence Collection (Locard's Exchange Principle)
    2. Error Spatter Reconstruction (Blood Spatter Analysis)
    3. Striation Matching (Ballistic Analysis)
    4. Luminol Scan (Hidden State Detection)
    5. Chain of Custody (Artifact Provenance)

    Args:
        run: The pipeline run to investigate.
        compare_runs: Optional list of runs for striation and custody comparison.
        bidirectional: Whether to check reverse traces.

    Returns:
        Complete Investigation with all analysis results.
    """
    # 1. Trace Evidence
    trace_result = analyze_traces(run, bidirectional=bidirectional)

    # 2. Error Spatter
    spatter_result = analyze_spatter(run)

    # 3. Striation Matching
    striation_matches: list[Any] = []
    if compare_runs:
        striation_matches = analyze_striations(run, compare_runs)

    # 4. Luminol Scan
    luminol_report = analyze_luminol(run)

    # 5. Chain of Custody
    custody_chain, custody_comparison = analyze_custody(
        run,
        compare_runs[0] if compare_runs else None,
    )

    # Build summary
    summary_parts: list[str] = []
    if trace_result.suspicious_transfers:
        summary_parts.append(
            f"{len(trace_result.suspicious_transfers)} suspicious trace transfers"
        )
    if spatter_result.stains:
        summary_parts.append(
            f"root cause estimated {spatter_result.origin_depth:.1f} stages before first error"
        )
    if striation_matches and striation_matches[0].same_root_cause:
        summary_parts.append(
            f"same root cause as build {striation_matches[0].build_id_2}"
        )
    if luminol_report.confirmed:
        summary_parts.append("hidden state corruption confirmed")
    if custody_comparison and custody_comparison.nondeterminism:
        summary_parts.append("nondeterminism detected")

    summary = "; ".join(summary_parts) if summary_parts else "No significant forensic findings"

    # Compute overall confidence
    confidence = _compute_investigation_confidence(
        trace_result, spatter_result, striation_matches, luminol_report
    )

    return Investigation(
        run_id=run.run_id,
        trace_result=trace_result,
        spatter_result=spatter_result,
        striation_matches=striation_matches,
        luminol_report=luminol_report,
        custody_chain=custody_chain,
        custody_comparison=custody_comparison,
        summary=summary,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc),
    )


def _compute_investigation_confidence(
    trace_result: TraceTransferResult,
    spatter_result: SpatterReconstruction,
    striation_matches: list[Any],
    luminol_report: Any,
) -> float:
    """Compute overall investigation confidence score."""
    scores: list[float] = []

    # Trace evidence confidence
    if trace_result.suspicious_transfers:
        max_suspicion = max(t.suspicion_score for t in trace_result.suspicious_transfers)
        scores.append(max_suspicion)

    # Spatter confidence
    if spatter_result.confidence > 0:
        scores.append(spatter_result.confidence)

    # Striation confidence
    if striation_matches:
        best_match = max(striation_matches, key=lambda m: m.correlation)
        if best_match.same_root_cause:
            scores.append(best_match.correlation)

    # Luminol confidence
    if luminol_report.confirmed:
        scores.append(0.9)

    if not scores:
        return 0.0

    # Average of available confidence scores
    return round(sum(scores) / len(scores), 2)
