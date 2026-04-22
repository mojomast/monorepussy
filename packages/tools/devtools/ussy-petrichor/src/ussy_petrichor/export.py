"""Export — drift history export in various formats."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import SoilDB


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Exporter:
    """Exports drift history in various formats (JSON, text)."""

    def __init__(self, db: SoilDB):
        self.db = db

    def export_json(self, days: int = 90, path: Optional[str] = None) -> str:
        """Export drift history as JSON.

        Args:
            days: Number of days of history.
            path: Optional specific path to export.

        Returns:
            JSON string.
        """
        if path:
            layers = self.db.get_layers(path, depth=1000)
        else:
            # Get all tracked paths
            paths = self.db.get_tracked_paths()
            layers = []
            for p in paths:
                layers.extend(self.db.get_layers(p, depth=1000))

        # Filter by date
        cutoff = _now().timestamp() - (days * 86400)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

        filtered = []
        for layer in layers:
            if layer["timestamp"] >= cutoff_dt:
                # Remove full content text for export (too large)
                export_layer = dict(layer)
                export_layer.pop("content_text", None)
                export_layer.pop("diff_text", None)
                filtered.append(export_layer)

        export_data = {
            "generated_at": _now().isoformat(),
            "days": days,
            "layer_count": len(filtered),
            "layers": filtered,
        }

        return json.dumps(export_data, indent=2, default=str)

    def export_text(self, days: int = 90, path: Optional[str] = None) -> str:
        """Export drift history as plain text summary.

        Args:
            days: Number of days of history.
            path: Optional specific path.

        Returns:
            Formatted text string.
        """
        if path:
            layers = self.db.get_layers(path, depth=1000)
        else:
            paths = self.db.get_tracked_paths()
            layers = []
            for p in paths:
                layers.extend(self.db.get_layers(p, depth=1000))

        # Filter by date
        cutoff = _now().timestamp() - (days * 86400)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

        filtered = [l for l in layers if l["timestamp"] >= cutoff_dt]

        lines = [
            f"Petrichor Export — {days} days",
            "═" * 47,
            f"Total layers: {len(filtered)}",
            f"Drift layers: {sum(1 for l in filtered if l['is_drift'])}",
        ]

        # Per-path summary
        path_counts: Dict[str, Dict] = {}
        for l in filtered:
            p = l["path"]
            if p not in path_counts:
                path_counts[p] = {"total": 0, "drifts": 0}
            path_counts[p]["total"] += 1
            if l["is_drift"]:
                path_counts[p]["drifts"] += 1

        for p, counts in path_counts.items():
            lines.append(f"  {p}: {counts['total']} layers, {counts['drifts']} drifts")

        return "\n".join(lines)

    def export(
        self,
        format: str = "json",
        days: int = 90,
        path: Optional[str] = None,
    ) -> str:
        """Export drift history in the specified format.

        Args:
            format: Output format ('json' or 'text').
            days: Number of days of history.
            path: Optional specific path.

        Returns:
            Formatted export string.
        """
        if format == "json":
            return self.export_json(days, path)
        elif format == "text":
            return self.export_text(days, path)
        else:
            raise ValueError(f"Unknown format: {format}. Use 'json' or 'text'.")
