"""Linter strictness adaptation for Circadia — adjusts linter rules based on cognitive zone."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ussy_circadia.zones import CognitiveZone
from ussy_circadia.config import CircadiaConfig, LinterConfig
from ussy_circadia.estimator import CircadianEstimator
from ussy_circadia.session import SessionTracker


# Fatigue error patterns that are more likely during circadian dips
FATIGUE_PATTERNS = {
    "off-by-one": {
        "description": "Off-by-one errors: < vs <=, range boundaries",
        "severity": "error",
        "pattern": "range\\(.*\\)|\\[.*:\\-?1\\]|\\[.*\\+1\\]",
    },
    "wrong-comparison": {
        "description": "Wrong comparison: = vs ==, < vs >, swapped operands",
        "severity": "error",
        "pattern": "if\\s+.*=[^=]",
    },
    "missing-null-check": {
        "description": "Missing null/None check before access",
        "severity": "warning",
        "pattern": "\\.get\\(|None\\s+and|if\\s+not\\s+\\w+\\s*:",
    },
    "assignment-in-condition": {
        "description": "Assignment in conditional (potential typo for ==)",
        "severity": "error",
        "pattern": "if\\s+\\w+\\s*=[^=]",
    },
}


@dataclass
class LinterRuleSet:
    """A set of linter rules with their configurations."""

    rules: List[str] = field(default_factory=list)
    severity_overrides: Dict[str, str] = field(default_factory=dict)
    disabled_rules: List[str] = field(default_factory=list)
    extra_patterns: List[str] = field(default_factory=list)


class LinterAdapter:
    """Adapts linter strictness based on the current cognitive zone.

    In GREEN zone: standard strictness
    In YELLOW zone: enhanced rules + fatigue patterns
    In RED zone: maximum strictness + all fatigue patterns
    In CREATIVE zone: relaxed, style-only warnings silenced
    """

    def __init__(
        self,
        config: Optional[CircadiaConfig] = None,
        estimator: Optional[CircadianEstimator] = None,
        session_tracker: Optional[SessionTracker] = None,
    ) -> None:
        """Initialize linter adapter.

        Args:
            config: Circadia configuration.
            estimator: Circadian state estimator.
            session_tracker: Session tracker.
        """
        self.config = config or CircadiaConfig()
        self.estimator = estimator or CircadianEstimator(
            utc_offset_hours=self.config.utc_offset_hours
        )
        self.session_tracker = session_tracker or SessionTracker()
        self._linter_config = self.config.linter

    def get_rules_for_zone(self, zone: CognitiveZone) -> LinterRuleSet:
        """Get the linter rule set for a given zone.

        Args:
            zone: The cognitive zone to get rules for.

        Returns:
            LinterRuleSet with appropriate rules.
        """
        if zone == CognitiveZone.GREEN:
            return LinterRuleSet(
                rules=list(self._linter_config.standard_rules),
            )
        elif zone == CognitiveZone.YELLOW:
            return LinterRuleSet(
                rules=list(self._linter_config.enhanced_rules),
                extra_patterns=list(self._linter_config.fatigue_error_patterns),
            )
        elif zone == CognitiveZone.RED:
            return LinterRuleSet(
                rules=list(self._linter_config.maximum_rules),
                severity_overrides={
                    "C": "error",  # Promote complexity warnings to errors
                    "R": "error",  # Promote refactoring suggestions to errors
                },
                extra_patterns=list(self._linter_config.fatigue_error_patterns),
            )
        elif zone == CognitiveZone.CREATIVE:
            return LinterRuleSet(
                rules=list(self._linter_config.relaxed_rules),
                disabled_rules=["W", "C", "R"],  # Disable style/refactor warnings
            )

        return LinterRuleSet(rules=list(self._linter_config.standard_rules))

    def get_current_rules(self) -> LinterRuleSet:
        """Get the linter rule set for the current cognitive zone.

        Returns:
            LinterRuleSet for the current zone.
        """
        from datetime import datetime, timezone

        session_hours = self.session_tracker.get_current_duration_hours()
        zone = self.estimator.current_zone(
            dt=datetime.now(timezone.utc),
            session_hours=session_hours,
        )
        return self.get_rules_for_zone(zone)

    def get_fatigue_patterns(self, zone: CognitiveZone) -> List[dict]:
        """Get fatigue error patterns relevant for a zone.

        Args:
            zone: The cognitive zone.

        Returns:
            List of fatigue pattern dicts.
        """
        if zone in (CognitiveZone.YELLOW, CognitiveZone.RED):
            return [
                {
                    "name": name,
                    **FATIGUE_PATTERNS[name],
                }
                for name in self._linter_config.fatigue_error_patterns
                if name in FATIGUE_PATTERNS
            ]
        return []

    def format_linter_config(self, zone: CognitiveZone) -> str:
        """Format linter configuration for a given zone as a readable string.

        Args:
            zone: The cognitive zone.

        Returns:
            Human-readable string describing the linter config.
        """
        rules = self.get_rules_for_zone(zone)
        patterns = self.get_fatigue_patterns(zone)

        lines = [
            f"Linter Configuration for {zone.icon} {zone.value.upper()} zone:",
            f"  Active rules: {', '.join(rules.rules) if rules.rules else 'none'}",
        ]
        if rules.disabled_rules:
            lines.append(f"  Disabled rules: {', '.join(rules.disabled_rules)}")
        if rules.severity_overrides:
            overrides = [
                f"{k} → {v}" for k, v in rules.severity_overrides.items()
            ]
            lines.append(f"  Severity overrides: {', '.join(overrides)}")
        if rules.extra_patterns:
            lines.append(f"  Fatigue patterns: {', '.join(rules.extra_patterns)}")
        if patterns:
            lines.append("  Fatigue pattern details:")
            for p in patterns:
                lines.append(f"    - {p['name']}: {p['description']}")

        return "\n".join(lines)
