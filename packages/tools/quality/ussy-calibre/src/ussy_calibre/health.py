"""Health aggregator — combines all instrument outputs into overall health report."""

from __future__ import annotations

from typing import Optional

from ussy_calibre.models import (
    ContaminationReport,
    FeedingReport,
    HealthReport,
    HoochReport,
    RiseResult,
    TestResult,
)
from ussy_calibre.instruments.hooch import HoochDetector, HoochDetectorWithHistory
from ussy_calibre.instruments.rise import RiseMeter
from ussy_calibre.instruments.contamination import ContaminationTracker
from ussy_calibre.instruments.feeding import FeedingSchedule
from ussy_calibre.instruments.thermal import ThermalProfiler


def compute_health(
    test_results: list[TestResult],
    test_history: Optional[list[list[TestResult]]] = None,
    source_map: Optional[dict[str, str]] = None,
    module_change_data: Optional[dict[str, dict]] = None,
) -> HealthReport:
    """Compute full health report from all instruments.

    Args:
        test_results: Current test results.
        test_history: Historical test runs.
        source_map: Mapping of filepath -> source code for assertion analysis.
        module_change_data: Feeding schedule data per module.

    Returns:
        Combined HealthReport.
    """
    # Hooch detection
    if test_history:
        hooch_detector = HoochDetectorWithHistory(history=test_history)
    else:
        hooch_detector = HoochDetector()
    hooch_report = hooch_detector.detect(test_results, source_map)

    # Rise meter
    rise_meter = RiseMeter()
    rise_result = rise_meter.measure(test_results)

    # Contamination tracker
    contamination_tracker = ContaminationTracker()
    contamination_report = contamination_tracker.track(test_history or [test_results])

    # Feeding schedule
    feeding_schedule = FeedingSchedule()
    feeding_report = feeding_schedule.audit(test_results, module_change_data)

    # Compute overall health score
    health_score = _aggregate_health_score(
        hooch_report, rise_result, contamination_report, feeding_report
    )

    # Generate diagnosis
    diagnosis = _generate_diagnosis(
        hooch_report, rise_result, contamination_report, feeding_report, health_score
    )

    return HealthReport(
        hooch=hooch_report,
        rise=rise_result,
        contamination=contamination_report,
        feeding=feeding_report,
        overall_health=health_score,
        diagnosis=diagnosis,
    )


def _aggregate_health_score(
    hooch: HoochReport,
    rise: RiseResult,
    contamination: ContaminationReport,
    feeding: FeedingReport,
) -> float:
    """Aggregate scores from all instruments into a single 0-100 health score."""
    # Hooch: lower hooch index = healthier (invert)
    hooch_score = max(0, 100 - hooch.overall_hooch_index)

    # Rise: direct score
    rise_score = rise.rise_score

    # Contamination: lower R0 = healthier
    cont_r0 = contamination.overall_r0
    if cont_r0 == 0:
        cont_score = 100.0
    elif cont_r0 < 1.0:
        cont_score = 80.0
    elif cont_r0 < 2.0:
        cont_score = 50.0
    else:
        cont_score = max(10, 100 - cont_r0 * 20)

    # Feeding: adherence * 100
    feed_score = feeding.overall_adherence * 100

    # Weighted average
    weights = {
        "hooch": 0.25,
        "rise": 0.30,
        "contamination": 0.25,
        "feeding": 0.20,
    }

    score = (
        hooch_score * weights["hooch"]
        + rise_score * weights["rise"]
        + cont_score * weights["contamination"]
        + feed_score * weights["feeding"]
    )

    return round(min(100.0, max(0.0, score)), 1)


def _generate_diagnosis(
    hooch: HoochReport,
    rise: RiseResult,
    contamination: ContaminationReport,
    feeding: FeedingReport,
    health_score: float,
) -> str:
    """Generate a fermentation-themed diagnosis."""
    if health_score >= 80:
        base = "Vigorous culture — your test suite is alive and discriminating."
    elif health_score >= 60:
        base = "Healthy but needs attention — some signs of neglect."
    elif health_score >= 40:
        base = "Ailing culture — significant issues need addressing."
    else:
        base = "Critical condition — the culture is at risk of collapse."

    details = []

    if hooch.overall_hooch_index > 30:
        details.append(
            f"High hooch index ({hooch.overall_hooch_index:.0f}%) — "
            "too many stale or trivial tests accumulating waste"
        )

    if rise.rise_score < 30:
        details.append(
            f"Flat rise (score {rise.rise_score:.0f}) — tests may not be discriminating"
        )

    if contamination.overall_r0 > 1.0:
        details.append(
            f"Contamination spreading (R0={contamination.overall_r0:.1f}) — "
            "flaky tests are infecting others"
        )

    if feeding.overall_adherence < 0.5:
        details.append("Poor feeding adherence — tests are not keeping up with code changes")

    if details:
        return base + " " + " | ".join(details)
    return base
