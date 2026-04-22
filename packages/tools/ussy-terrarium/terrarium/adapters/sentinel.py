"""sentinelussy adapter — maps anomaly detections to organism immune responses."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class SentinelAdapter(BaseAdapter):
    """Adapter for sentinelussy JSON output.

    Expected JSON format::

        {
          "files": {
            "/path/to/file.py": {
              "anomaly_score": 0.73,
              "severity": "ELEVATED",
              "is_anomalous": true,
              "num_detectors_fired": 1,
              "detections": [
                {
                  "detector_id": "D-0028",
                  "pattern_name": "complex_function",
                  "false_positive_rate": 0.2
                }
              ]
            }
          }
        }

    The adapter maps non-self activations to ``anomaly_active`` markers.
    Detectors with a high false-positive rate (> 0.5) are treated as
    background noise and suppressed.
    """

    name = "sentinel"

    FP_SUPPRESSION_THRESHOLD = 0.5

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load sentinelussy data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        files = data.get("files", {})
        if not files:
            # Also support top-level detections array with source_file
            detections = data.get("detections", [])
            files = self._group_detections_by_file(detections)

        states: Dict[str, OrganismHealthState] = {}
        for path, file_info in files.items():
            is_anomalous = file_info.get("is_anomalous", False)
            anomaly_score = file_info.get("anomaly_score", 0.0)
            detections = file_info.get("detections", [])

            # Suppress if all fired detectors have high false-positive rates
            if detections and all(
                d.get("false_positive_rate", 0.0) > self.FP_SUPPRESSION_THRESHOLD
                for d in detections
            ):
                is_anomalous = False
                anomaly_score = 0.0

            vitality = 1.0 - min(anomaly_score, 1.0)
            states[path] = OrganismHealthState(
                path=path,
                vitality=vitality,
                anomaly_active=is_anomalous,
            )

        return states

    @staticmethod
    def _group_detections_by_file(detections: list) -> Dict[str, dict]:
        """Group a flat detections list into a per-file mapping."""
        files: Dict[str, dict] = {}
        for det in detections:
            path = det.get("source_file", "")
            if not path:
                continue
            if path not in files:
                files[path] = {
                    "is_anomalous": True,
                    "anomaly_score": 0.0,
                    "detections": [],
                }
            files[path]["detections"].append(det)
            files[path]["anomaly_score"] = max(
                files[path]["anomaly_score"],
                det.get("strength", 0.0),
            )
        return files
