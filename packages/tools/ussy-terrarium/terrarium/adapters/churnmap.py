"""churnmap adapter — maps territory/community clusters to organism biomes."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class ChurnmapAdapter(BaseAdapter):
    """Adapter for churnmap JSON output.

    Expected JSON format::

        {
          "territories": [
            {
              "territory_id": "core-api",
              "modules": ["core/api", "core/db"]
            }
          ],
          "files": {
            "src/auth.py": {"territory_id": "core-api"},
            "src/utils.py": {"territory_id": "ui-layer"}
          }
        }

    The adapter maps each file to a ``territory_id`` representing the
    community/cluster it belongs to. This is purely visual metadata — it
    does not affect vitality or health scores.
    """

    name = "churnmap"

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load churnmap data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        states: Dict[str, OrganismHealthState] = {}

        # Direct file-to-territory mapping takes precedence
        files = data.get("files", {})
        for path, info in files.items():
            if isinstance(info, dict):
                territory_id = info.get("territory_id")
            else:
                territory_id = info
            if territory_id is not None:
                states[path] = OrganismHealthState(
                    path=path,
                    territory_id=str(territory_id) if territory_id else None,
                )

        # Also support deriving from territory->modules mapping
        territories = data.get("territories", [])
        for territory in territories:
            territory_id = territory.get("territory_id")
            if territory_id is None:
                continue
            modules = territory.get("modules", [])
            for module in modules:
                # Only map actual file-like paths, skip bare directories
                if not module.endswith(".py"):
                    continue
                # Skip if already mapped from the files section
                if module not in states:
                    states[module] = OrganismHealthState(
                        path=module,
                        territory_id=str(territory_id),
                    )

        return states
