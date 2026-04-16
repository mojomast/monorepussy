"""Terminal zone indicator for Circadia — shows current cognitive zone in the prompt."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from circadia.zones import CognitiveZone, ZoneProbability
from circadia.estimator import CircadianEstimator
from circadia.config import CircadiaConfig
from circadia.session import SessionTracker


class TerminalIndicator:
    """Generates terminal prompt indicators based on current cognitive zone."""

    # Shell escape sequences for zone colors
    COLORS = {
        CognitiveZone.GREEN: "\033[32m",     # Green
        CognitiveZone.YELLOW: "\033[33m",    # Yellow
        CognitiveZone.RED: "\033[31m",       # Red
        CognitiveZone.CREATIVE: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(
        self,
        config: Optional[CircadiaConfig] = None,
        estimator: Optional[CircadianEstimator] = None,
        session_tracker: Optional[SessionTracker] = None,
    ) -> None:
        """Initialize terminal indicator.

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

    def _get_zone_prob(self, dt: Optional[datetime] = None) -> ZoneProbability:
        """Get current zone probability distribution."""
        session_hours = self.session_tracker.get_current_duration_hours()
        return self.estimator.estimate(dt, session_hours)

    def get_zone(self, dt: Optional[datetime] = None) -> CognitiveZone:
        """Get current dominant zone."""
        return self._get_zone_prob(dt).dominant_zone

    def short_indicator(self, dt: Optional[datetime] = None) -> str:
        """Generate a short prompt indicator (just the icon).

        Returns:
            String like "🟢" for green zone.
        """
        zone = self.get_zone(dt)
        return zone.icon

    def colored_indicator(self, dt: Optional[datetime] = None) -> str:
        """Generate a colored prompt indicator with zone name.

        Returns:
            String like "\033[32m🟢 green\033[0m" for green zone.
        """
        zone = self.get_zone(dt)
        color = self.COLORS[zone]
        return f"{color}{zone.icon} {zone.value}{self.RESET}"

    def full_indicator(self, dt: Optional[datetime] = None) -> str:
        """Generate a full prompt indicator with zone, confidence, and session info.

        Returns:
            Multi-line string with detailed zone information.
        """
        prob = self._get_zone_prob(dt)
        zone = prob.dominant_zone
        color = self.COLORS[zone]
        session_hours = self.session_tracker.get_current_duration_hours()

        lines = [
            f"{self.BOLD}{color}{zone.icon} {zone.value.upper()} ZONE{self.RESET}",
            f"  Confidence: {prob.confidence:.0%}",
            f"  Description: {zone.description}",
            f"  Linter: {zone.linter_strictness}",
            f"  Deploy allowed: {'yes' if zone.deploy_allowed else 'no'}",
            f"  Risky git: {'allowed' if zone.risky_git_allowed else 'restricted'}",
        ]

        if session_hours > 0:
            hours = int(session_hours)
            mins = int((session_hours - hours) * 60)
            lines.append(f"  Session: {hours}h {mins}m")

        lines.append("")
        lines.append("  Zone probabilities:")
        for z in CognitiveZone:
            p = prob.get_probability(z)
            bar_len = int(p * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"    {z.icon} {z.value:8s} {bar} {p:.0%}")

        return "\n".join(lines)

    def shell_prompt_string(self, dt: Optional[datetime] = None) -> str:
        """Generate a string suitable for embedding in PS1.

        Returns:
            String like "🟢" for embedding in shell prompt.
        """
        return self.short_indicator(dt)

    def bash_prompt_integration(self) -> str:
        """Generate bash code to add Circadia to PS1.

        Returns:
            Bash code string for eval.
        """
        return (
            'export PS1="$(circadia status --prompt) $PS1"'
        )

    def zsh_prompt_integration(self) -> str:
        """Generate zsh code to add Circadia to PROMPT.

        Returns:
            Zsh code string for eval.
        """
        return (
            'export PROMPT="$(circadia status --prompt) $PROMPT"'
        )
