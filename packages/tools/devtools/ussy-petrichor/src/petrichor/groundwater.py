"""Groundwater — latent drift detection (declared vs. effective vs. intended)."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .db import SoilDB
from .hash import string_hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GroundwaterLayer:
    """Represents the three-layer state of a configuration:

    - Declared: what the config file says
    - Effective: what the running process is using
    - Intended: what the IaC defines
    """

    def __init__(
        self,
        path: str,
        declared_hash: str = "",
        declared_text: str = "",
        effective_hash: str = "",
        effective_text: str = "",
        intended_hash: str = "",
        intended_text: str = "",
    ):
        self.path = path
        self.declared_hash = declared_hash
        self.declared_text = declared_text
        self.effective_hash = effective_hash
        self.effective_text = effective_text
        self.intended_hash = intended_hash
        self.intended_text = intended_text

    @property
    def is_consistent(self) -> bool:
        """All three layers agree."""
        if not self.declared_hash:
            return True
        hashes = {self.declared_hash, self.effective_hash, self.intended_hash}
        hashes.discard("")
        return len(hashes) <= 1

    @property
    def latent_drift(self) -> bool:
        """Declared != Effective — process running with drifted value."""
        return bool(self.declared_hash and self.effective_hash and
                     self.declared_hash != self.effective_hash)

    @property
    def config_drift(self) -> bool:
        """Declared != Intended — file doesn't match IaC."""
        return bool(self.declared_hash and self.intended_hash and
                     self.declared_hash != self.intended_hash)

    @property
    def deep_drift(self) -> bool:
        """Effective != Intended — process not running desired config."""
        return bool(self.effective_hash and self.intended_hash and
                     self.effective_hash != self.intended_hash)


class GroundwaterDetector:
    """Detects latent drift by comparing declared, effective, and intended states."""

    def __init__(self, db: SoilDB):
        self.db = db

    def analyze(self, path: str) -> GroundwaterLayer:
        """Analyze the three-layer state of a configuration.

        Args:
            path: File path to analyze.

        Returns:
            GroundwaterLayer with the analysis results.
        """
        # Declared state: from the latest soil layer
        declared_hash = ""
        declared_text = ""
        latest = self.db.get_latest_layer(path)
        if latest:
            declared_hash = latest["content_hash"]
            declared_text = latest["content_text"]

        # Intended state: from the desired_state table
        intended_hash = ""
        intended_text = ""
        desired = self.db.get_desired_state(path)
        if desired:
            intended_hash = desired["desired_hash"]
            intended_text = desired.get("desired_text", "")

        # Effective state: we set this to match declared by default
        # (would need runtime extraction for real services)
        effective_hash = declared_hash
        effective_text = declared_text

        return GroundwaterLayer(
            path=path,
            declared_hash=declared_hash,
            declared_text=declared_text,
            effective_hash=effective_hash,
            effective_text=effective_text,
            intended_hash=intended_hash,
            intended_text=intended_text,
        )

    def analyze_with_effective(
        self,
        path: str,
        effective_text: str,
    ) -> GroundwaterLayer:
        """Analyze with an explicitly provided effective (runtime) state.

        Args:
            path: File path.
            effective_text: The runtime/effective configuration text.

        Returns:
            GroundwaterLayer with the analysis results.
        """
        layer = self.analyze(path)
        layer.effective_text = effective_text
        layer.effective_hash = string_hash(effective_text)
        return layer

    def analyze_all(self) -> List[GroundwaterLayer]:
        """Analyze groundwater for all tracked paths.

        Returns:
            List of GroundwaterLayer results.
        """
        paths = self.db.get_tracked_paths()
        return [self.analyze(p) for p in paths]

    def format_groundwater(self, path: Optional[str] = None) -> str:
        """Format groundwater analysis as a human-readable string.

        Args:
            path: Optional specific path. If None, analyzes all tracked.

        Returns:
            Formatted string.
        """
        if path:
            layers = [self.analyze(path)]
        else:
            layers = self.analyze_all()

        lines = [
            "Groundwater Detection",
            "═" * 47,
        ]

        for gw in layers:
            lines.append("")
            lines.append(f"{gw.path}:")

            # Declared
            declared_status = ""
            if gw.config_drift:
                declared_status = " ← doesn't match IaC"
            lines.append(f"  Declared:  {gw.declared_hash[:12]}...{declared_status}")

            # Effective
            effective_status = ""
            if gw.latent_drift:
                effective_status = " ← RUNNING with drifted value"
            elif gw.is_consistent:
                effective_status = " ← consistent"
            lines.append(f"  Effective: {gw.effective_hash[:12]}...{effective_status}")

            # Intended
            intended_status = ""
            if gw.intended_hash:
                if gw.declared_hash == gw.intended_hash:
                    intended_status = " ← matches IaC"
                else:
                    intended_status = " ← DIFFERS from declared"
            lines.append(f"  Intended:  {gw.intended_hash[:12]}...{intended_status}")

            # Diagnosis
            if gw.latent_drift:
                lines.append("  ⚠️ Process was restarted WITH drift, not FROM desired state")
                lines.append("  → The file was corrected but the service wasn't reloaded")
            elif gw.is_consistent and gw.declared_hash:
                lines.append("  ✅ All three layers agree")
            elif gw.config_drift:
                lines.append("  ⚠️ Config file doesn't match intended IaC state")

        return "\n".join(lines)
