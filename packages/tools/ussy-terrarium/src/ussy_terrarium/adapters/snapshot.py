"""snapshotussy adapter — maps dev state snapshots to organism memory markers."""

import json
from typing import Dict, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


class SnapshotAdapter(BaseAdapter):
    """Adapter for snapshotussy (dev state snapshots).

    Expected JSON format (from ``peek()`` output)::

        {
          "name": "before-refactor",
          "created_at": "2024-01-15T10:00:00+00:00",
          "open_files": [{"path": "src/auth.py", "modified": true}],
          "processes": [{"command": "pytest"}],
          "env_var_count": 12,
          "note": "Working on auth module"
        }

    The adapter maps snapshot data to a memory pressure score (0.0–1.0)
    based on open file count and process count. High pressure = organism
    is overloaded with context.
    """

    name = "snapshot"

    STUB_MODE: bool = False

    def __init__(self, data_path: Optional[str] = None) -> None:
        super().__init__(data_path=data_path)
        self._real = None
        try:
            from snapshot.core import peek

            self._real = peek
            self.STUB_MODE = False
        except Exception:
            self.STUB_MODE = True

    def load(self) -> Dict[str, OrganismHealthState]:
        """Load snapshot data and map to organism health states.

        Returns:
            Mapping of file path to OrganismHealthState.
        """
        if not self.data_path:
            return {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        open_files = data.get("open_files", [])
        processes = data.get("processes", [])
        env_var_count = data.get("env_var_count", 0)

        # Compute memory pressure: more open files + processes = higher pressure
        file_pressure = min(len(open_files) / 20.0, 1.0)
        process_pressure = min(len(processes) / 10.0, 1.0)
        env_pressure = min(env_var_count / 50.0, 1.0)
        pressure_score = min(
            (file_pressure + process_pressure + env_pressure) / 3.0, 1.0
        )

        vitality = max(0.0, 1.0 - pressure_score * 0.25)

        states: Dict[str, OrganismHealthState] = {}

        # Map each open file to a health state
        for file_info in open_files:
            path = file_info.get("path", "")
            if not path:
                continue
            modified = file_info.get("modified", False)
            file_vitality = vitality * (0.8 if modified else 1.0)
            states[path] = OrganismHealthState(
                path=path,
                vitality=file_vitality,
            )

        # If no open files, emit a state for the snapshot root/note
        if not states:
            name = data.get("name", "snapshot")
            states[name] = OrganismHealthState(
                path=name,
                vitality=vitality,
            )

        return states
