"""Annealing Scheduler — Controlled Stabilization Protocol."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_calibre.models import AnnealingPhase, AnnealingSchedule, StressReport, TestResult


def estimate_complexity(
    test_name: str,
    results: Optional[List[TestResult]] = None,
    lines_of_code: int = 0,
    num_assertions: int = 0,
    num_dependencies: int = 0,
) -> float:
    """Estimate test complexity (analogous to glass thickness).

    Complexity determines soak time — thicker glass needs longer annealing.
    """
    base = 1.0
    base += lines_of_code * 0.01
    base += num_assertions * 0.05
    base += num_dependencies * 0.1
    return max(base, 0.5)


def generate_soak_phase(
    test_name: str,
    complexity: float,
    target_pass_rate: float = 0.95,
) -> AnnealingPhase:
    """Generate the soak phase — run in most stable environment.

    Duration proportional to test complexity (thickness).
    """
    steps = max(int(complexity * 5), 3)

    return AnnealingPhase(
        phase_name="soak",
        description=(
            f"Run '{test_name}' in most stable environment "
            f"(single-threaded, pinned versions, isolated state) "
            f"until {target_pass_rate:.0%} consistent pass rate achieved"
        ),
        duration_steps=steps,
        environment_changes=[],
        target_pass_rate=target_pass_rate,
    )


def generate_cooling_phase(
    test_name: str,
    current_stress: float,
    max_stress: float = 1.0,
    max_rate: float = 0.1,
) -> AnnealingPhase:
    """Generate controlled cooling phase.

    Gradually introduce environmental variation: first parallelism,
    then version drift, then load. After each change, verify the
    test still passes consistently.

    Cooling rate: d(env_var)/dt = max_rate × (1 - σ_current/σ_max)
    """
    if max_stress > 0:
        cooling_rate = max_rate * (1.0 - current_stress / max_stress)
    else:
        cooling_rate = max_rate

    # Steps needed based on stress level
    steps = max(int(current_stress / cooling_rate), 2) if cooling_rate > 0 else 1

    env_changes = []
    if current_stress > 0.3:
        env_changes.append("Introduce parallelism (2 workers)")
    if current_stress > 0.2:
        env_changes.append("Allow Python version drift (+0.1)")
    if current_stress > 0.1:
        env_changes.append("Introduce load simulation (25%)")
    if current_stress > 0.0:
        env_changes.append("Full CI environment")

    return AnnealingPhase(
        phase_name="controlled_cool",
        description=(
            f"Gradually introduce environmental variation for '{test_name}'. "
            f"Cooling rate: {cooling_rate:.3f}/step based on current stress "
            f"({current_stress:.3f}/{max_stress:.3f})"
        ),
        duration_steps=steps,
        environment_changes=env_changes,
        target_pass_rate=0.90,
    )


def generate_free_cool_phase(
    test_name: str,
) -> AnnealingPhase:
    """Generate free cool phase — below strain point, no new stress forms.

    Once the test passes across all target environments, it's annealed.
    """
    return AnnealingPhase(
        phase_name="free_cool",
        description=(
            f"'{test_name}' has passed all target environments. "
            "Add to full CI suite — no new stress can form below strain point."
        ),
        duration_steps=1,
        environment_changes=["Add to full CI suite"],
        target_pass_rate=0.95,
    )


def generate_annealing_schedule(
    test_name: str,
    stress_report: Optional[StressReport] = None,
    complexity: float = 1.0,
    target_pass_rate: float = 0.95,
) -> AnnealingSchedule:
    """Generate a complete annealing schedule for a test.

    Three phases: soak → controlled cool → free cool.
    Re-soak triggered if pass rate drops below threshold during cooling.
    """
    current_stress = stress_report.total_stress if stress_report else 0.5

    soak = generate_soak_phase(test_name, complexity, target_pass_rate)
    cool = generate_cooling_phase(test_name, current_stress)
    free = generate_free_cool_phase(test_name)

    total_steps = soak.duration_steps + cool.duration_steps + free.duration_steps

    # Add re-soak if stress is high
    phases = [soak]
    if current_stress > 0.3:
        re_soak = AnnealingPhase(
            phase_name="re-soak",
            description=(
                f"High stress detected ({current_stress:.3f}). "
                "Return to stable environment before continuing cooling."
            ),
            duration_steps=max(int(complexity * 3), 2),
            environment_changes=[],
            target_pass_rate=target_pass_rate,
        )
        phases.append(re_soak)
        total_steps += re_soak.duration_steps

    phases.append(cool)
    phases.append(free)

    return AnnealingSchedule(
        test_name=test_name,
        phases=phases,
        estimated_total_steps=total_steps,
        complexity_factor=complexity,
    )


def generate_schedules(
    stress_reports: Dict[str, StressReport],
    complexities: Optional[Dict[str, float]] = None,
    target_pass_rate: float = 0.95,
) -> Dict[str, AnnealingSchedule]:
    """Generate annealing schedules for all tests with detectable stress."""
    schedules: Dict[str, AnnealingSchedule] = {}

    for test_name, report in stress_reports.items():
        complexity = complexities.get(test_name, 1.0) if complexities else 1.0
        schedules[test_name] = generate_annealing_schedule(
            test_name, report, complexity, target_pass_rate
        )

    return schedules


def format_schedule(schedule: AnnealingSchedule) -> str:
    """Format a single annealing schedule as readable output."""
    lines = []
    lines.append(f"  Annealing Schedule for: {schedule.test_name}")
    lines.append(f"  Complexity Factor: {schedule.complexity_factor:.2f}")
    lines.append(f"  Estimated Total Steps: {schedule.estimated_total_steps}")
    lines.append("")

    for i, phase in enumerate(schedule.phases, 1):
        lines.append(f"  Phase {i}: {phase.phase_name.upper()}")
        lines.append(f"    {phase.description}")
        lines.append(f"    Duration: {phase.duration_steps} steps")
        lines.append(f"    Target Pass Rate: {phase.target_pass_rate:.0%}")
        if phase.environment_changes:
            lines.append("    Environment Changes:")
            for change in phase.environment_changes:
                lines.append(f"      → {change}")
        lines.append("")

    return "\n".join(lines)


def format_schedules(schedules: Dict[str, AnnealingSchedule]) -> str:
    """Format all annealing schedules."""
    lines = []
    lines.append("=" * 60)
    lines.append("ANNEALING SCHEDULER — Controlled Stabilization Protocol")
    lines.append("=" * 60)
    lines.append("")

    if not schedules:
        lines.append("No stressed tests require annealing.")
        return "\n".join(lines)

    sorted_schedules = sorted(
        schedules.values(),
        key=lambda s: s.estimated_total_steps,
        reverse=True,
    )

    for schedule in sorted_schedules:
        lines.append(format_schedule(schedule))

    lines.append(f"Total: {len(schedules)} test(s) require annealing")

    return "\n".join(lines)
