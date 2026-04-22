"""kompressiussy adapter — maps Kolmogorov complexity estimates to organism density."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class KompressiAdapter(BaseAdapter):
    """Adapter for kompressiussy JSON output.

    Expected JSON format (serialized ``FileProfile`` list)::

        [
          {
            "path": "/path/to/file.py",
            "ae": 1442.0,
            "ar": 0.6674,
            "id": 10.15,
            "is_anomaly": false
          }
        ]

    The adapter maps each file's **information density** (``id`` = ae/loc)
    to a ``complexity_score`` (0.0–1.0). High density = high complexity =
    worse vitality.
    """

    name = "kompressi"

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load kompressiussy data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        profiles = data if isinstance(data, list) else []
        if not profiles:
            return {}

        # Normalize against max information density in the batch
        max_id = max((p.get("id", 0.0) for p in profiles), default=1.0)
        if max_id <= 0:
            max_id = 1.0

        states: Dict[str, OrganismHealthState] = {}
        for profile in profiles:
            path = profile.get("path", "")
            if not path:
                continue
            info_density = profile.get("id", 0.0)
            complexity_score = min(info_density / max_id, 1.0)

            vitality = max(0.0, 1.0 - complexity_score * 0.2)

            states[path] = OrganismHealthState(
                path=path,
                vitality=vitality,
                complexity_score=complexity_score,
            )

        return states
