"""Local probe registry — store and retrieve probes locally."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from ussy_stratax.models import Probe


class LocalRegistry:
    """Local filesystem-based registry for behavioral probes."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), ".strata", "registry")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_probe(self, probe: Probe) -> str:
        """Store a probe in the local registry. Returns the probe ID."""
        probe_id = f"{probe.package}::{probe.function}::{probe.name}"
        probe_dir = self.base_dir / probe.package / probe.function
        probe_dir.mkdir(parents=True, exist_ok=True)

        probe_file = probe_dir / f"{probe.name}.json"
        with open(probe_file, "w") as f:
            json.dump(probe.to_dict(), f, indent=2)

        return probe_id

    def get_probe(self, package: str, function: str, name: str) -> Optional[Probe]:
        """Retrieve a specific probe."""
        probe_file = self.base_dir / package / function / f"{name}.json"
        if not probe_file.exists():
            return None

        with open(probe_file, "r") as f:
            data = json.load(f)

        return Probe(
            name=data["name"],
            package=data["package"],
            function=data["function"],
            input_data=data.get("input_data"),
            expected_output=data.get("expected_output"),
            output_has_keys=data.get("output_has_keys"),
            target_mutated=data.get("target_mutated"),
            raises=data.get("raises"),
            returns_type=data.get("returns_type"),
            custom_assertion=data.get("custom_assertion"),
        )

    def list_probes(self, package: Optional[str] = None) -> List[Probe]:
        """List probes, optionally filtered by package."""
        probes = []

        if package:
            search_dirs = [self.base_dir / package]
        else:
            search_dirs = [self.base_dir]

        for search_dir in search_dirs:
            if not search_dir.is_dir():
                continue
            for json_file in search_dir.rglob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)
                    probes.append(
                        Probe(
                            name=data["name"],
                            package=data["package"],
                            function=data["function"],
                            input_data=data.get("input_data"),
                            expected_output=data.get("expected_output"),
                            output_has_keys=data.get("output_has_keys"),
                            target_mutated=data.get("target_mutated"),
                            raises=data.get("raises"),
                            returns_type=data.get("returns_type"),
                            custom_assertion=data.get("custom_assertion"),
                        )
                    )
                except (json.JSONDecodeError, KeyError):
                    continue

        return probes

    def delete_probe(self, package: str, function: str, name: str) -> bool:
        """Delete a probe from the local registry."""
        probe_file = self.base_dir / package / function / f"{name}.json"
        if probe_file.exists():
            probe_file.unlink()
            return True
        return False

    def get_packages(self) -> List[str]:
        """List all packages with stored probes."""
        if not self.base_dir.is_dir():
            return []
        return [
            d.name
            for d in self.base_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def probe_count(self, package: Optional[str] = None) -> int:
        """Count probes, optionally filtered by package."""
        return len(self.list_probes(package))
