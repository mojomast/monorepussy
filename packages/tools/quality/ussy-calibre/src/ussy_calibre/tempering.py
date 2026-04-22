"""Tempering Detector — Brittleness vs. Stability Discrimination."""

from __future__ import annotations

from typing import Dict, List, Optional

from ussy_calibre.models import BrittlenessClass, TemperResult, TestResult

# Brittleness thresholds
BRITTLENESS_TEMPERED_THRESHOLD = 0.3
BRITTLENESS_CRACKED_THRESHOLD = 0.7


def compute_pass_rate(results: List[bool]) -> float:
    """Compute pass rate from a list of boolean outcomes."""
    if not results:
        return 0.0
    return sum(results) / len(results)


def detect_tempering(
    results_with_hardening: List[TestResult],
    results_without_hardening: List[TestResult],
    tempered_threshold: float = BRITTLENESS_TEMPERED_THRESHOLD,
    cracked_threshold: float = BRITTLENESS_CRACKED_THRESHOLD,
) -> Dict[str, TemperResult]:
    """Detect tempered (brittle-stable) tests.

    A tempered test passes consistently with retries/timeouts but fails
    without them. The brittleness index B(t) measures this:

    B(t) = max(0, (p_hard - p_raw) / max(p_hard, ε))

    B = 0: truly annealed (stable with or without hardening)
    B = 1: fully tempered (only passes with hardening)
    """
    # Group by test name
    hard_by_test: Dict[str, List[bool]] = {}
    for r in results_with_hardening:
        if r.test_name not in hard_by_test:
            hard_by_test[r.test_name] = []
        hard_by_test[r.test_name].append(r.passed)

    raw_by_test: Dict[str, List[bool]] = {}
    for r in results_without_hardening:
        if r.test_name not in raw_by_test:
            raw_by_test[r.test_name] = []
        raw_by_test[r.test_name].append(r.passed)

    results: Dict[str, TemperResult] = {}

    all_tests = set(hard_by_test.keys()) | set(raw_by_test.keys())

    for test_name in all_tests:
        p_hard = compute_pass_rate(hard_by_test.get(test_name, []))
        p_raw = compute_pass_rate(raw_by_test.get(test_name, []))

        # Brittleness index
        eps = 1e-10
        brittleness = max(0.0, (p_hard - p_raw) / max(p_hard, eps))

        # Classification
        if p_hard < 0.5:
            bclass = BrittlenessClass.CRACKED
        elif brittleness >= cracked_threshold:
            bclass = BrittlenessClass.CRACKED
        elif brittleness >= tempered_threshold:
            bclass = BrittlenessClass.TEMPERED
        else:
            bclass = BrittlenessClass.ANNEALED

        results[test_name] = TemperResult(
            test_name=test_name,
            pass_rate_with_hardening=p_hard,
            pass_rate_without_hardening=p_raw,
            brittleness_index=brittleness,
            brittleness_class=bclass,
        )

    return results


def detect_tempering_from_results(
    all_results: List[TestResult],
    tempered_threshold: float = BRITTLENESS_TEMPERED_THRESHOLD,
    cracked_threshold: float = BRITTLENESS_CRACKED_THRESHOLD,
) -> Dict[str, TemperResult]:
    """Detect tempering from mixed results by using retry/timeout as the
    hardening indicator.

    Results with retries_used > 0 or timeout_used = True are 'hardened'.
    Results without are 'raw'.
    """
    hardening: List[TestResult] = []
    raw: List[TestResult] = []

    for r in all_results:
        if r.retries_used > 0 or r.timeout_used:
            hardening.append(r)
        else:
            raw.append(r)

    # If no separation possible, treat all as raw (no hardening detected)
    if not hardening and raw:
        results: Dict[str, TemperResult] = {}
        by_test: Dict[str, List[bool]] = {}
        for r in raw:
            if r.test_name not in by_test:
                by_test[r.test_name] = []
            by_test[r.test_name].append(r.passed)

        for test_name, outcomes in by_test.items():
            p = compute_pass_rate(outcomes)
            if p < 0.5:
                bclass = BrittlenessClass.CRACKED
            elif p < 0.8:
                bclass = BrittlenessClass.TEMPERED
            else:
                bclass = BrittlenessClass.ANNEALED

            results[test_name] = TemperResult(
                test_name=test_name,
                pass_rate_with_hardening=p,
                pass_rate_without_hardening=p,
                brittleness_index=0.0,
                brittleness_class=bclass,
            )
        return results

    return detect_tempering(
        hardening, raw, tempered_threshold, cracked_threshold
    )


def format_temper_report(results: Dict[str, TemperResult]) -> str:
    """Format tempering detection results."""
    lines = []
    lines.append("=" * 60)
    lines.append("TEMPERING DETECTOR — Brittleness vs. Stability")
    lines.append("=" * 60)
    lines.append("")

    if not results:
        lines.append("No test results to analyze.")
        return "\n".join(lines)

    sorted_results = sorted(
        results.values(), key=lambda r: r.brittleness_index, reverse=True
    )

    for result in sorted_results:
        status_icon = {
            BrittlenessClass.ANNEALED: "✓",
            BrittlenessClass.TEMPERED: "⚠️",
            BrittlenessClass.CRACKED: "✗",
        }
        icon = status_icon.get(result.brittleness_class, "?")
        lines.append(f"  {icon} {result.test_name}")
        lines.append(
            f"    Brittleness: {result.brittleness_index:.4f} "
            f"[{result.brittleness_class.value.upper()}]"
        )
        lines.append(
            f"    Pass Rate: {result.pass_rate_with_hardening:.2%} "
            f"(hardened) vs {result.pass_rate_without_hardening:.2%} (raw)"
        )

        if result.is_tempered:
            lines.append(
                "    ⚠️  RECOMMEND: Re-anneal this test instead of adding more hardening"
            )
        lines.append("")

    annealed = sum(1 for r in results.values() if r.brittleness_class == BrittlenessClass.ANNEALED)
    tempered = sum(1 for r in results.values() if r.brittleness_class == BrittlenessClass.TEMPERED)
    cracked = sum(1 for r in results.values() if r.brittleness_class == BrittlenessClass.CRACKED)
    total = len(results)

    lines.append(f"Summary: {annealed} annealed, {tempered} tempered, {cracked} cracked (of {total})")

    return "\n".join(lines)
