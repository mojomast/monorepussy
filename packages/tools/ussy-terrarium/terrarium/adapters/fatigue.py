"""fatigueussy adapter — maps Paris' Law crack growth to organism wound levels."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class FatigueAdapter(BaseAdapter):
    """Adapter for fatigueussy JSON output.

    Expected JSON format (from ``fatigue scan --format json``)::

        {
          "stress_intensities": {
            "/path/to/file.py": {"K": 29.48, "delta_K": 5.2},
            ...
          },
          "cracks": [...],
          "critical": [...]
        }

    The adapter maps each file's stress intensity factor (``K``) to a
    ``crack_intensity`` score (0.0–1.0). High ``K`` and high ``delta_K``
    mean a visibly dying organism.
    """

    name = "fatigue"

    DEFAULT_MAX_K_CEILING = 100.0

    def __init__(
        self, data_path: Optional[str] = None, max_k_ceiling: Optional[float] = None
    ) -> None:
        super().__init__(data_path=data_path)
        self.max_k_ceiling = (
            max_k_ceiling if max_k_ceiling is not None else self.DEFAULT_MAX_K_CEILING
        )

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load fatigueussy data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stress_intensities = data.get("stress_intensities", {})
        if not stress_intensities:
            return {}

        # Compute max K for normalization. Use a fixed ceiling as the
        # denominator so healthy repos with low absolute K values don't
        # produce false critical scores.
        raw_max_k = max(
            (si.get("K", 0.0) for si in stress_intensities.values()), default=1.0
        )
        max_k = self.max_k_ceiling
        if max_k <= 0:
            max_k = 1.0

        states: Dict[str, OrganismHealthState] = {}
        for path, si in stress_intensities.items():
            k = si.get("K", 0.0)
            delta_k = si.get("delta_K", 0.0)

            # Normalize crack intensity 0.0–1.0 against capped max
            crack_intensity = min(k / max_k, 1.0)

            # Increase intensity if crack is actively growing
            if delta_k > 0 and max_k > 0:
                growth_factor = min(delta_k / max_k, 1.0)
                crack_intensity = min(crack_intensity + growth_factor * 0.3, 1.0)

            states[path] = OrganismHealthState(
                path=path,
                vitality=1.0 - crack_intensity,
                crack_intensity=crack_intensity,
            )

        return states
