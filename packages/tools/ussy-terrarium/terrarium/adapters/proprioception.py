"""proprioceptionussy adapter — maps workspace drift and body schema to organism awareness."""

import json
from pathlib import Path
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class ProprioceptionAdapter(BaseAdapter):
    """Adapter for proprioceptionussy (workspace drift + body schema).

    Expected JSON format (from ``build_schema()`` output)::

        {
          "root": "/path/to/project",
          "limbs": [
            {
              "path": "/path/to/project/src",
              "type": "git-repo",
              "state": {"head": "main", "dirty": true}
            }
          ]
        }

    The adapter maps workspace schema data to a drift score (0.0–1.0)
    based on how many limbs are in a dirty/modified state.
    """

    name = "proprioception"

    STUB_MODE: bool = False

    def __init__(self, data_path: Optional[str] = None) -> None:
        super().__init__(data_path=data_path)
        self._real = None
        try:
            from propriocept.schema import build_schema

            self._real = build_schema
            self.STUB_MODE = False
        except Exception:
            self.STUB_MODE = True

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load proprioception data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        limbs = data.get("limbs", [])
        if not limbs:
            return {}

        total = len(limbs)
        dirty = sum(1 for limb in limbs if limb.get("state", {}).get("dirty", False))
        drift_score = min(dirty / max(total, 1), 1.0)

        root = data.get("root", "")
        states: Dict[str, OrganismHealthState] = {}
        for limb in limbs:
            path = limb.get("path", "")
            if not path:
                continue
            # Map each limb path to a health state with the global drift score
            states[path] = OrganismHealthState(
                path=path,
                vitality=max(0.0, 1.0 - drift_score * 0.3),
            )

        # Also emit a state for the root itself
        if root:
            states[root] = OrganismHealthState(
                path=root,
                vitality=max(0.0, 1.0 - drift_score * 0.3),
            )

        return states
