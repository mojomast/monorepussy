"""Lehr Engine — Orchestrates all instruments for full analysis."""

from __future__ import annotations

from typing import Dict, List, Optional

from ussy_calibre.models import (
    AnnealingSchedule,
    CTEProfile,
    GlassClassification,
    ShockResistance,
    StressReport,
    SuiteReport,
    TemperResult,
    TestResult,
)
from ussy_calibre.birefringence import scan_birefringence
from ussy_calibre.cte import profile_cte
from ussy_calibre.thermal_shock import test_thermal_shock
from ussy_calibre.annealing import generate_schedules
from ussy_calibre.tempering import detect_tempering_from_results
from ussy_calibre.classifier_lehr import classify_tests


def analyze(
    results: List[TestResult],
    stress_threshold: float = 0.1,
    target_pass_rate: float = 0.95,
    complexities: Optional[Dict[str, float]] = None,
) -> SuiteReport:
    """Run full Lehr analysis on test results.

    Orchestrates all 6 instruments:
    1. Birefringence Scanner — stress visualization
    2. CTE Profiler — environment sensitivity
    3. Thermal Shock Tester — rapid change resilience
    4. Annealing Scheduler — stabilization protocols
    5. Tempering Detector — brittleness discrimination
    6. Glass Type Classifier — fragility taxonomy
    """
    # 1. Birefringence scan
    stress_reports = scan_birefringence(results, stress_threshold)

    # 2. CTE profiles
    cte_profiles = profile_cte(results)

    # 3. Thermal shock test (using CTE values)
    cte_by_test = {name: p.composite_cte for name, p in cte_profiles.items()}
    shock_resistances = test_thermal_shock(results, cte_by_test)

    # 4. Annealing schedules (for stressed tests)
    stressed_reports = {
        name: report for name, report in stress_reports.items() if report.is_stressed
    }
    if not stressed_reports and stress_reports:
        # If no tests are stressed, generate schedules for all (they'll be trivial)
        stressed_reports = stress_reports
    annealing_schedules = generate_schedules(stressed_reports, complexities, target_pass_rate)

    # 5. Tempering detection
    temper_results = detect_tempering_from_results(results)

    # 6. Glass type classification
    glass_classifications = classify_tests(cte_profiles, shock_resistances, temper_results)

    # Build suite report
    test_names = list(set(r.test_name for r in results) if results else [])

    return SuiteReport(
        tests=test_names,
        stress_reports=stress_reports,
        cte_profiles=cte_profiles,
        shock_resistances=shock_resistances,
        annealing_schedules=annealing_schedules,
        temper_results=temper_results,
        glass_classifications=glass_classifications,
    )


def format_report(report: SuiteReport) -> str:
    """Format a complete suite report."""
    from ussy_calibre.birefringence import format_stress_map
    from ussy_calibre.cte import format_cte_profiles
    from ussy_calibre.thermal_shock import format_shock_report
    from ussy_calibre.annealing import format_schedules
    from ussy_calibre.tempering import format_temper_report
    from ussy_calibre.classifier import format_classifications

    lines = []
    lines.append("=" * 60)
    lines.append("LEHR — Glass Annealing Science for Test Suite Stabilization")
    lines.append("=" * 60)
    lines.append("")

    # Overview
    lines.append(f"Tests Analyzed: {len(report.tests)}")
    lines.append(f"Suite Health: {report.suite_health:.2%}")
    lines.append(f"Tempered Tests: {report.tempered_count}")
    lines.append("")

    # Glass distribution
    lines.append("Glass Distribution:")
    for gtype, count in sorted(report.glass_distribution.items()):
        lines.append(f"  {gtype}: {count}")
    lines.append("")

    # Detailed reports
    lines.append(format_stress_map(report.stress_reports))
    lines.append("")
    lines.append(format_cte_profiles(report.cte_profiles))
    lines.append("")
    lines.append(format_shock_report(report.shock_resistances))
    lines.append("")
    lines.append(format_schedules(report.annealing_schedules))
    lines.append("")
    lines.append(format_temper_report(report.temper_results))
    lines.append("")
    lines.append(format_classifications(report.glass_classifications))

    return "\n".join(lines)
