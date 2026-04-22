"""seralussy adapter — maps ecological succession stages to organism visual age."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class SeralAdapter(BaseAdapter):
    """Adapter for seralussy JSON output.

    Expected JSON format (from ``.seral/stages.json``)::

        {
          "src/auth": "climax",
          "src/new": "pioneer",
          "src/payments": "seral_mid",
          "src/legacy": "disturbed"
        }

    The adapter maps each module's successional stage to a
    ``succession_stage`` string: ``pioneer``, ``seral``, or ``climax``.

    Mapping rules::

        pioneer, disturbed        → "pioneer"
        seral_early, seral_mid,
        seral_late                → "seral"
        climax                    → "climax"

    This is a neutral visual marker — it does not affect vitality.
    """

    name = "seral"

    STAGE_MAP = {
        "pioneer": "pioneer",
        "disturbed": "pioneer",
        "seral_early": "seral",
        "seral_mid": "seral",
        "seral_late": "seral",
        "climax": "climax",
    }

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load seralussy data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        states: Dict[str, OrganismHealthState] = {}
        for path, stage in data.items():
            if not isinstance(stage, str):
                continue
            mapped = self.STAGE_MAP.get(stage, "seral")
            states[path] = OrganismHealthState(
                path=path,
                succession_stage=mapped,
            )

        return states
