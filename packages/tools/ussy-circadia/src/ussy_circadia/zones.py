"""Cognitive zone definitions and probability distributions."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class CognitiveZone(enum.Enum):
    """Cognitive performance zones based on circadian state."""

    GREEN = "green"       # Peak performance
    YELLOW = "yellow"     # Moderate performance
    RED = "red"           # Low performance / high risk
    CREATIVE = "creative" # Relaxed / creative mode

    @property
    def icon(self) -> str:
        """Terminal icon for the zone."""
        icons = {
            CognitiveZone.GREEN: "🟢",
            CognitiveZone.YELLOW: "🟡",
            CognitiveZone.RED: "🔴",
            CognitiveZone.CREATIVE: "🎨",
        }
        return icons[self]

    @property
    def description(self) -> str:
        """Human-readable description of the zone."""
        descriptions = {
            CognitiveZone.GREEN: "Peak performance — full capabilities enabled",
            CognitiveZone.YELLOW: "Moderate performance — enhanced safeguards active",
            CognitiveZone.RED: "Low performance — maximum protections active",
            CognitiveZone.CREATIVE: "Creative mode — exploratory work encouraged",
        }
        return descriptions[self]

    @property
    def linter_strictness(self) -> str:
        """Linter strictness level for this zone."""
        levels = {
            CognitiveZone.GREEN: "standard",
            CognitiveZone.YELLOW: "enhanced",
            CognitiveZone.RED: "maximum",
            CognitiveZone.CREATIVE: "relaxed",
        }
        return levels[self]

    @property
    def deploy_allowed(self) -> bool:
        """Whether production deployment is allowed in this zone."""
        return self in (CognitiveZone.GREEN, CognitiveZone.CREATIVE)

    @property
    def risky_git_allowed(self) -> bool:
        """Whether risky git operations (force push, hard reset) are allowed."""
        return self == CognitiveZone.GREEN


@dataclass
class ZoneProbability:
    """Probability distribution over cognitive zones.

    Uses Bayesian-style estimation from time-of-day and session duration.
    """

    green: float = 0.25
    yellow: float = 0.25
    red: float = 0.25
    creative: float = 0.25

    def __post_init__(self) -> None:
        """Normalize probabilities to sum to 1.0."""
        total = self.green + self.yellow + self.red + self.creative
        if total <= 0:
            self.green = 0.25
            self.yellow = 0.25
            self.red = 0.25
            self.creative = 0.25
        else:
            self.green /= total
            self.yellow /= total
            self.red /= total
            self.creative /= total

    @property
    def dominant_zone(self) -> CognitiveZone:
        """Return the zone with highest probability."""
        probs = {
            CognitiveZone.GREEN: self.green,
            CognitiveZone.YELLOW: self.yellow,
            CognitiveZone.RED: self.red,
            CognitiveZone.CREATIVE: self.creative,
        }
        return max(probs, key=probs.get)  # type: ignore[arg-type]

    @property
    def confidence(self) -> float:
        """Return the probability of the dominant zone."""
        return max(self.green, self.yellow, self.red, self.creative)

    def get_probability(self, zone: CognitiveZone) -> float:
        """Get probability for a specific zone."""
        mapping = {
            CognitiveZone.GREEN: self.green,
            CognitiveZone.YELLOW: self.yellow,
            CognitiveZone.RED: self.red,
            CognitiveZone.CREATIVE: self.creative,
        }
        return mapping[zone]
