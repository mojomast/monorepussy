"""Health scoring dataclass for the Terrarium ecosystem."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class HealthScore:
    """Unified health score across all ussyverse data sources.

    All fields are normalized to 0.0–1.0 where:
    - 1.0 = perfect health / no issues detected
    - 0.0 = critical / maximum issues detected
    """

    overall: float = 1.0
    fatigue: float = 1.0
    epidemic: float = 1.0
    anomaly: float = 1.0
    drift: float = 1.0
    churn: float = 1.0
    complexity: float = 1.0
    territory: str = ""
    succession: str = "seral"

    # Raw adapter metrics for debugging/extension
    raw: Dict[str, Dict] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize to a plain dictionary."""
        return {
            "overall": round(self.overall, 4),
            "fatigue": round(self.fatigue, 4),
            "epidemic": round(self.epidemic, 4),
            "anomaly": round(self.anomaly, 4),
            "drift": round(self.drift, 4),
            "churn": round(self.churn, 4),
            "complexity": round(self.complexity, 4),
            "territory": self.territory,
            "succession": self.succession,
        }
