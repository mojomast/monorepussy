"""Full Metrological Characterization Report generator."""

from __future__ import annotations

from typing import List, Optional

from calibre.models import (
    CapabilityResult,
    CapabilitySpec,
    DriftObservation,
    DriftResult,
    FlakinessClassification,
    RRSummary,
    TestRun,
    TraceabilityLink,
    TraceabilityResult,
    UncertaintyBudget,
)
from calibre.budget import budget_from_test_runs, format_budget
from calibre.capability import capability_analysis, format_capability
from calibre.classifier import classify_test, format_classification
from calibre.drift import analyze_drift, format_drift_result
from calibre.rr import compute_rr_summary, format_rr_summary, runs_to_rr_observations
from calibre.traceability import audit_traceability, format_traceability


def generate_full_report(
    suite: str,
    runs: List[TestRun],
    drift_observations: Optional[List[DriftObservation]] = None,
    traceability_links: Optional[List[TraceabilityLink]] = None,
    capability_specs: Optional[List[CapabilitySpec]] = None,
    mpe: float = 0.1,
) -> str:
    """Generate a complete Metrological Characterization Report.

    Includes all six instruments:
    1. Uncertainty Budget
    2. R&R Study
    3. Capability Index
    4. Uncertainty Classifier
    5. Drift Detector
    6. Traceability Auditor
    """
    sections: List[str] = []

    # Header
    sections.append("=" * 70)
    sections.append(f"  METROLOGICAL CHARACTERIZATION REPORT")
    sections.append(f"  Suite: {suite}")
    sections.append("=" * 70)
    sections.append("")

    # 1. Uncertainty Budget
    budget = budget_from_test_runs(suite, runs)
    sections.append(format_budget(budget))

    # 2. R&R Study
    rr_obs = runs_to_rr_observations(runs)
    rr_summary = compute_rr_summary(suite, rr_obs)
    sections.append(format_rr_summary(rr_summary))

    # 3. Capability Index
    if capability_specs:
        for spec in capability_specs:
            spec_runs = [r for r in runs if r.test_name == spec.test_name]
            cap_result = capability_analysis(spec_runs, spec)
            sections.append(format_capability(cap_result))
    else:
        # Default spec: pass rate between 0.8 and 1.0
        default_spec = CapabilitySpec(
            test_name=suite,
            usl=1.0,
            lsl=0.8,
        )
        cap_result = capability_analysis(runs, default_spec)
        sections.append(format_capability(cap_result))

    # 4. Uncertainty Classifier
    unique_tests = list(set(r.test_name for r in runs))
    for test_name in unique_tests[:5]:  # Top 5 most interesting
        classification = classify_test(runs, test_name)
        sections.append(format_classification(classification))

    # 5. Drift Detector
    if drift_observations:
        by_test: dict = {}
        for obs in drift_observations:
            by_test.setdefault(obs.test_name, []).append(obs)

        for test_name, obs_list in by_test.items():
            drift_result = analyze_drift(obs_list, mpe=mpe)
            sections.append(format_drift_result(drift_result))
    else:
        sections.append("Drift Analysis: No drift observations provided")
        sections.append("")

    # 6. Traceability Auditor
    if traceability_links:
        by_test: dict = {}
        for link in traceability_links:
            by_test.setdefault(link.test_name, []).append(link)

        # Also check for orphan tests
        tests_with_links = set(by_test.keys())
        for test_name in unique_tests:
            links = by_test.get(test_name, [])
            trace_result = audit_traceability(test_name, links)
            sections.append(format_traceability(trace_result))
    else:
        sections.append("Traceability Audit: No traceability links provided")
        sections.append("")

    # Summary
    sections.append("=" * 70)
    sections.append("  SUMMARY")
    sections.append("=" * 70)
    sections.append("")
    sections.append(f"  Total test runs analyzed: {len(runs)}")
    sections.append(f"  Unique tests: {len(unique_tests)}")
    sections.append(f"  Dominant uncertainty source: {budget.dominant_source or 'N/A'}")
    sections.append(f"  R&R Category: {rr_summary.category.value}")
    sections.append("")

    return "\n".join(sections)
