"""Soil Profile — layered history visualization."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .db import SoilDB
from .diff import extract_changed_keys
from .soil import SoilMemory


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SoilProfiler:
    """Generates soil profile visualizations showing layered drift history."""

    def __init__(self, db: SoilDB):
        self.db = db
        self.soil = SoilMemory(db)

    def profile(self, path: str, depth: int = 10) -> str:
        """Generate a soil profile for a path.

        Shows the layered drift history with diagnosis.

        Args:
            path: File path.
            depth: Maximum number of layers to show.

        Returns:
            Formatted soil profile string.
        """
        abs_path = path
        layers = self.db.get_layers(abs_path, depth)

        if not layers:
            return f"No soil layers found for {abs_path}"

        lines = [
            f"Petrichor Soil Profile: {abs_path}",
            "═" * 55,
        ]

        # Check for correction pattern
        correction = self.soil.detect_correction(abs_path)

        for i, layer in enumerate(layers):
            is_surface = i == 0
            layer_num = len(layers) - i

            # Time description
            try:
                ts = datetime.fromisoformat(layer["timestamp"])
                age = _now() - ts
                if age.total_seconds() < 3600:
                    time_desc = "NOW" if is_surface else f"{int(age.total_seconds() / 60)} min ago"
                elif age.total_seconds() < 86400:
                    time_desc = f"{int(age.total_seconds() / 3600)} hours ago"
                else:
                    time_desc = f"{int(age.total_seconds() / 86400)} days ago"
            except (ValueError, TypeError):
                time_desc = "unknown"

            # Surface label
            surface_label = " (Surface)" if is_surface else ""
            lines.append("")
            lines.append(f"Layer {layer_num}{surface_label} — {time_desc}")

            # Drift status
            if layer["is_drift"]:
                # Find changed keys
                changed = []
                if layer.get("diff_text"):
                    # Try to extract keys from the diff
                    prev_layers = layers[i + 1:] if i + 1 < len(layers) else []
                    if prev_layers:
                        changed = extract_changed_keys(
                            prev_layers[0]["content_text"], layer["content_text"]
                        )
                keys_str = ", ".join(changed) if changed else "(see diff)"
                lines.append(f"  {keys_str}  ← DRIFTED")

                # Actor info
                if layer.get("actor"):
                    lines.append(f"  Drifted by: {layer['actor']}")
                if layer.get("context"):
                    lines.append(f"  Context: {layer['context']}")

                # Recurrence info
                drift_layers = [l for l in layers if l["is_drift"] and l["content_hash"] == layer["content_hash"]]
                if len(drift_layers) > 1:
                    lines.append(f"  This drift pattern: RECURRING ({len(drift_layers)} times in profile)")
            else:
                lines.append(f"  Content hash: {layer['content_hash'][:16]}...  ← Desired state")

                # Stability info
                if i + 1 < len(layers):
                    try:
                        current_ts = datetime.fromisoformat(layer["timestamp"])
                        prev_ts = datetime.fromisoformat(layers[i + 1]["timestamp"])
                        stable_days = (prev_ts - current_ts).days
                        if stable_days > 0:
                            lines.append(f"  Stable for: {stable_days} days")
                    except (ValueError, TypeError):
                        pass

        # Diagnosis
        if correction:
            lines.append("")
            lines.append(f"DIAGNOSIS: The desired state causes repeated drift.")
            lines.append(f"           The drift to hash {correction['recurring_hash'][:12]}... is actually a CORRECTION, not a bug.")
            lines.append(f"           → Update desired state to match the recurring value")
            lines.append(f"           → This file has been fighting its config ({correction['recurrence_count']} recurring drifts)")

        return "\n".join(lines)

    def brief(self, path: str) -> str:
        """Generate a brief one-line summary for a path.

        Args:
            path: File path.

        Returns:
            Brief summary string.
        """
        abs_path = path
        layers = self.db.get_layers(abs_path, 1)
        if not layers:
            return f"{abs_path}: no data"

        latest = layers[0]
        drift_count = self.db.get_drift_count(abs_path)
        status = "DRIFTED" if latest["is_drift"] else "OK"
        return f"{abs_path}: {status} ({drift_count} drifts recorded)"
