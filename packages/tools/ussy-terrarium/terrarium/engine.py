"""TerrariumEngine — collects, scores, and serializes ecosystem health."""

import json
from typing import Dict, List, Optional

from .health import HealthScore
from .adapters.base import BaseAdapter


class TerrariumEngine:
    """Central engine that orchestrates adapter collection and health scoring.

    Args:
        adapters: List of initialized adapter instances.
    """

    def __init__(self, adapters: List[BaseAdapter]) -> None:
        self.adapters = adapters
        self._last_collected: Optional[Dict[str, Dict]] = None

    def collect(self) -> Dict[str, Dict]:
        """Call each adapter's ``get_metrics()`` and merge into a unified dict.

        Returns:
            Mapping of adapter name ->; loaded metrics dict.
        """
        collected: Dict[str, Dict] = {}
        for adapter in self.adapters:
            try:
                states = adapter.load()
                collected[adapter.name] = {
                    "count": len(states),
                    "states": {
                        path: self._state_to_dict(state)
                        for path, state in states.items()
                    },
                    "stub": getattr(adapter, "STUB_MODE", False),
                }
            except Exception as exc:
                collected[adapter.name] = {"error": str(exc), "stub": True}
        self._last_collected = collected
        return collected

    @staticmethod
    def _state_to_dict(state) -> Dict:
        """Convert an OrganismHealthState to a plain dict."""
        return {
            "vitality": state.vitality,
            "crack_intensity": state.crack_intensity,
            "infection_state": state.infection_state,
            "anomaly_active": state.anomaly_active,
            "complexity_score": state.complexity_score,
            "territory_id": state.territory_id,
            "succession_stage": state.succession_stage,
        }

    def score(self) -> HealthScore:
        """Compute a 0.0–1.0 overall ecosystem health score from merged metrics.

        The algorithm averages the inverse of each damage signal:
        - fatigue: 1.0 - mean(crack_intensity)
        - epidemic: ratio of non-infected files
        - anomaly: ratio of non-anomalous files
        - drift: 1.0 - mean(1.0 - vitality where vitality < 1.0)
        - complexity: 1.0 - mean(complexity_score)
        """
        if self._last_collected is None:
            self.collect()

        collected = self._last_collected or {}
        health = HealthScore()
        health.raw = collected

        # Fatigue score
        fatigue_data = collected.get("fatigue", {})
        if "states" in fatigue_data:
            intensities = [
                s["crack_intensity"] for s in fatigue_data["states"].values()
            ]
            health.fatigue = (
                1.0 - (sum(intensities) / len(intensities)) if intensities else 1.0
            )

        # Epidemic score
        endemic_data = collected.get("endemic", {})
        if "states" in endemic_data:
            states_list = list(endemic_data["states"].values())
            infected = sum(1 for s in states_list if s["infection_state"] == "I")
            health.epidemic = (
                1.0 - (infected / len(states_list)) if states_list else 1.0
            )

        # Anomaly score
        sentinel_data = collected.get("sentinel", {})
        if "states" in sentinel_data:
            states_list = list(sentinel_data["states"].values())
            anomalous = sum(1 for s in states_list if s["anomaly_active"])
            health.anomaly = (
                1.0 - (anomalous / len(states_list)) if states_list else 1.0
            )

        # Drift score (from proprioception or any adapter reporting vitality < 1.0)
        drift_values = []
        for adapter_name, data in collected.items():
            if "states" in data:
                for state in data["states"].values():
                    if state["vitality"] < 1.0:
                        drift_values.append(1.0 - state["vitality"])
        health.drift = (
            1.0 - (sum(drift_values) / len(drift_values)) if drift_values else 1.0
        )

        # Complexity score
        kompressi_data = collected.get("kompressi", {})
        if "states" in kompressi_data:
            scores = [s["complexity_score"] for s in kompressi_data["states"].values()]
            health.complexity = 1.0 - (sum(scores) / len(scores)) if scores else 1.0

        # Territory / succession from first available adapter
        for adapter_name in ("churnmap", "seral"):
            data = collected.get(adapter_name, {})
            if "states" in data and data["states"]:
                first = next(iter(data["states"].values()))
                if adapter_name == "churnmap":
                    health.territory = first.get("territory_id", "")
                elif adapter_name == "seral":
                    health.succession = first.get("succession_stage", "seral")

        # Overall: weighted average of sub-scores
        weights = {
            "fatigue": 0.20,
            "epidemic": 0.20,
            "anomaly": 0.20,
            "drift": 0.15,
            "complexity": 0.15,
            "churn": 0.10,
        }
        overall = 0.0
        total_weight = 0.0
        for key, weight in weights.items():
            overall += getattr(health, key) * weight
            total_weight += weight

        health.overall = overall / total_weight if total_weight > 0 else 1.0
        return health

    def to_json(self) -> str:
        """Serialize the current collected state and score to JSON."""
        score = self.score()
        payload = {
            "health": score.to_dict(),
            "adapters": self._last_collected or {},
        }
        return json.dumps(payload, indent=2)
