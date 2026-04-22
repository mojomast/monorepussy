"""endemicussy adapter — maps SIR/SEIR infection states to organism contagion."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class EndemicAdapter(BaseAdapter):
    """Adapter for endemicussy JSON output.

    Expected JSON format::

        {
          "modules": [
            {
              "path": "/path/to/file.py",
              "compartment": "I",
              "patterns": ["bare-except"]
            }
          ]
        }

    Or a flat mapping::

        {
          "/path/to/file.py": {
            "compartment": "I",
            "patterns": ["bare-except"]
          }
        }

    The adapter maps each file's compartment to an ``infection_state``:
    ``S`` (susceptible), ``E`` (exposed), ``I`` (infected), ``R`` (recovered).
    Infected files get a "contagion glow" (red tint). Files in ``R`` state
    are scarred but stable.
    """

    name = "endemic"

    VALID_STATES = {"S", "E", "I", "R"}

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load endemicussy data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        states: Dict[str, OrganismHealthState] = {}

        # Support "modules" list format
        modules = data.get("modules", [])
        if modules:
            for module in modules:
                path = module.get("path", "")
                if not path:
                    continue
                compartment = module.get("compartment", "S")
                if compartment not in self.VALID_STATES:
                    compartment = "S"
                vitality = self._vitality_for_state(compartment)
                states[path] = OrganismHealthState(
                    path=path,
                    vitality=vitality,
                    infection_state=compartment,
                )
            return states

        # Support flat mapping format
        for path, info in data.items():
            if not isinstance(info, dict):
                continue
            # Skip metadata keys that don't look like file paths
            if "/" not in path and "\\" not in path and not path.endswith(".py"):
                continue
            compartment = info.get("compartment", "S")
            if compartment not in self.VALID_STATES:
                compartment = "S"
            vitality = self._vitality_for_state(compartment)
            states[path] = OrganismHealthState(
                path=path,
                vitality=vitality,
                infection_state=compartment,
            )

        return states

    @staticmethod
    def _vitality_for_state(state: str) -> float:
        if state == "S":
            return 1.0
        elif state == "E":
            return 0.7
        elif state == "I":
            return 0.3
        elif state == "R":
            return 0.8
        return 1.0
