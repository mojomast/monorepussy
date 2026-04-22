"""Diagnosis engine — generate natural-language health reports."""

from dataclasses import dataclass, field
from typing import List, Optional

from .organisms import Vitality, VITALITY_COLORS, ANSI_RESET, ANSI_BOLD
from .model import Organism, CHURN_THRESHOLD, COMPLEXITY_THRESHOLD, COVERAGE_THRESHOLD


@dataclass
class Diagnosis:
    """A medical-style diagnosis for an unhealthy module."""

    path: str
    vitality: Vitality = Vitality.HEALTHY
    symptoms: List[str] = field(default_factory=list)
    diagnosis_text: str = ""
    treatment: str = ""
    prognosis: str = ""
    priority: str = "LOW"

    def format_report(self) -> str:
        """Format the diagnosis as a human-readable report."""
        lines = []

        # Header
        vitality_str = self.vitality.value.upper()
        lines.append(f"🩺 {self.path} — {vitality_str}")
        lines.append("")

        # Symptoms
        if self.symptoms:
            lines.append("Symptoms:")
            for symptom in self.symptoms:
                lines.append(f"  - {symptom}")
            lines.append("")

        # Diagnosis
        if self.diagnosis_text:
            lines.append(f"Diagnosis: {self.diagnosis_text}")
            lines.append("")

        # Treatment
        if self.treatment:
            lines.append(f"Treatment: {self.treatment}")
            lines.append("")

        # Prognosis
        if self.prognosis:
            lines.append(f"Prognosis: {self.prognosis} Priority: {self.priority}.")

        return "\n".join(lines)


def diagnose(organism: Organism) -> Diagnosis:
    """Generate a diagnosis for an organism.

    Args:
        organism: The organism to diagnose.

    Returns:
        A Diagnosis with natural-language health report.
    """
    diag = Diagnosis(
        path=organism.path,
        vitality=organism.vitality,
        symptoms=organism.symptoms[:],
    )

    # Determine priority
    if organism.health < 20:
        diag.priority = "CRITICAL"
    elif organism.health < 40:
        diag.priority = "HIGH"
    elif organism.health < 60:
        diag.priority = "MEDIUM"
    else:
        diag.priority = "LOW"

    # Generate diagnosis text based on symptoms
    has_churn = any("churn" in s.lower() for s in organism.symptoms)
    has_complexity = any("complexity" in s.lower() for s in organism.symptoms)
    has_coverage = any("coverage" in s.lower() for s in organism.symptoms)
    has_bugs = any("bug" in s.lower() for s in organism.symptoms)
    is_dead = any("dead" in s.lower() for s in organism.symptoms)
    is_deprecated = any("deprecated" in s.lower() for s in organism.symptoms)

    if is_dead:
        diag.diagnosis_text = (
            "This module is dead code — it has not been maintained in a very long time. "
            "It may be safe to remove entirely, or it may have hidden dependents."
        )
        diag.treatment = (
            "Verify no other modules import from this file, then remove it. "
            "If dependents exist, consider migrating them to a maintained alternative."
        )
        diag.prognosis = "Will continue to decay. Removal recommended."
    elif is_deprecated:
        diag.diagnosis_text = (
            "This module is deprecated and decaying. It should not be used for new code."
        )
        diag.treatment = (
            "Remove or replace with the recommended alternative. "
            "Update all callers to use the new API."
        )
        diag.prognosis = "Will worsen as the codebase evolves away from it."
    elif has_churn and has_complexity and has_coverage:
        diag.diagnosis_text = (
            "This module is overworked and under-tested. The high churn "
            "suggests it's serving too many responsibilities. "
            "High complexity makes it error-prone, and low test coverage "
            "means bugs can hide undetected."
        )
        diag.treatment = (
            "Consider splitting into smaller, focused modules. "
            "Add comprehensive tests before refactoring (pinning behavior). "
            "Reduce complexity by extracting helper functions."
        )
        diag.prognosis = "Will worsen without intervention."
    elif has_churn and has_complexity:
        diag.diagnosis_text = (
            "This module is under heavy development pressure. "
            "High churn combined with high complexity suggests it's a hotspot "
            "that accumulates technical debt rapidly."
        )
        diag.treatment = (
            "Stabilize the API first, then refactor incrementally. "
            "Consider whether the module's responsibilities can be split."
        )
        diag.prognosis = "At risk of becoming unmaintainable."
    elif has_churn:
        diag.diagnosis_text = (
            "This module changes frequently, which may indicate unstable requirements "
            "or that it's a bottleneck for many features."
        )
        diag.treatment = (
            "Investigate why changes are so frequent. Consider if the module "
            "needs a more stable interface or if requirements can be consolidated."
        )
        diag.prognosis = "Moderate risk if complexity doesn't increase."
    elif has_complexity:
        diag.diagnosis_text = (
            "This module has high cyclomatic complexity, making it hard to "
            "understand, test, and maintain."
        )
        diag.treatment = (
            "Refactor complex functions into smaller, composable pieces. "
            "Use early returns, guard clauses, and polymorphism to reduce branching."
        )
        diag.prognosis = "Manageable with targeted refactoring."
    elif has_coverage:
        diag.diagnosis_text = (
            "This module lacks adequate test coverage. Without tests, "
            "regressions can go undetected (weak immune system)."
        )
        diag.treatment = (
            "Add tests covering the main code paths. Focus on edge cases "
            "and error handling first."
        )
        diag.prognosis = "Good prognosis — testing is straightforward to add."
    elif has_bugs:
        diag.diagnosis_text = (
            "This module has active bugs that need attention."
        )
        diag.treatment = "Investigate and fix reported bugs. Add regression tests."
        diag.prognosis = "Will improve once bugs are resolved."
    elif organism.health >= 80:
        diag.diagnosis_text = "This module is healthy and well-maintained."
        diag.treatment = "No treatment needed. Continue current practices."
        diag.prognosis = "Excellent. Maintain current health practices."
    else:
        diag.diagnosis_text = "This module has some minor issues but is generally stable."
        diag.treatment = "Monitor for changes. Address symptoms as they arise."
        diag.prognosis = "Good with minor attention."

    return diag
