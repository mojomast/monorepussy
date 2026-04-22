"""Load and parse probe definition files (YAML)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ussy_stratax.models import Probe


class ProbeLoader:
    """Load behavioral probes from YAML files."""

    def __init__(self, probe_dirs: Optional[List[str]] = None):
        self.probe_dirs = probe_dirs or []
        # Add built-in probes directory
        builtin = os.path.join(os.path.dirname(__file__), "..", "data", "probes")
        builtin = os.path.normpath(builtin)
        if os.path.isdir(builtin):
            self.probe_dirs.append(builtin)

    def load_file(self, path: str) -> List[Probe]:
        """Load probes from a single YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        return self._parse_probe_data(data)

    def load_dir(self, dir_path: str) -> List[Probe]:
        """Load all probe files from a directory."""
        probes = []
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            return probes

        for yaml_file in sorted(dir_path.glob("*.yml")):
            probes.extend(self.load_file(str(yaml_file)))
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            probes.extend(self.load_file(str(yaml_file)))

        return probes

    def load_all(self) -> List[Probe]:
        """Load probes from all configured directories."""
        probes = []
        for dir_path in self.probe_dirs:
            probes.extend(self.load_dir(dir_path))
        return probes

    def load_for_package(self, package: str) -> List[Probe]:
        """Load probes targeting a specific package."""
        all_probes = self.load_all()
        return [p for p in all_probes if p.package == package]

    def _parse_probe_data(self, data: Dict[str, Any]) -> List[Probe]:
        """Parse YAML data into Probe objects."""
        probes = []
        package = data.get("package", "")
        function = data.get("function", "")

        for probe_def in data.get("probes", []):
            probe = Probe(
                name=probe_def.get("name", "unnamed"),
                package=package,
                function=function,
                input_data=probe_def.get("input"),
                expected_output=probe_def.get("output"),
                output_has_keys=probe_def.get("output_has_keys"),
                target_mutated=probe_def.get("target_mutated"),
                raises=probe_def.get("raises"),
                returns_type=probe_def.get("returns_type"),
                custom_assertion=probe_def.get("custom_assertion"),
            )
            probes.append(probe)

        return probes

    @staticmethod
    def parse_yaml_string(yaml_str: str) -> List[Probe]:
        """Parse a YAML string into Probe objects."""
        data = yaml.safe_load(yaml_str)
        if not data:
            return []
        loader = ProbeLoader()
        return loader._parse_probe_data(data)
