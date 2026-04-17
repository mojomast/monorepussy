"""Run behavioral probes against package versions."""

from __future__ import annotations

import importlib
import time
from typing import Any, Callable, Dict, List, Optional

from strata.models import Probe, ProbeResult, VersionProbeResult


class ProbeRunner:
    """Execute behavioral probes against installed or specified package versions."""

    def __init__(self, sandbox: bool = True, timeout: float = 10.0):
        self.sandbox = sandbox
        self.timeout = timeout
        self._cache: Dict[str, Any] = {}

    def run_probe(self, probe: Probe, package_version: str = "") -> ProbeResult:
        """Run a single probe and return the result."""
        start = time.time()
        try:
            # Try to import and run the probe
            actual_output = self._execute_probe(probe)
            elapsed = (time.time() - start) * 1000

            passed = self._check_assertion(probe, actual_output)
            return ProbeResult(
                probe_name=probe.name,
                package=probe.package,
                version=package_version,
                passed=passed,
                actual_output=actual_output,
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ProbeResult(
                probe_name=probe.name,
                package=probe.package,
                version=package_version,
                passed=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    def run_probes(
        self, probes: List[Probe], package_version: str = ""
    ) -> List[ProbeResult]:
        """Run multiple probes and return all results."""
        return [self.run_probe(p, package_version) for p in probes]

    def run_probes_for_version(
        self, probes: List[Probe], package: str, version: str
    ) -> VersionProbeResult:
        """Run all probes against a specific package version."""
        results = self.run_probes(probes, version)
        return VersionProbeResult(
            package=package,
            version=version,
            results=results,
        )

    def _execute_probe(self, probe: Probe) -> Any:
        """Execute the probe by calling the target function with input data."""
        try:
            module = importlib.import_module(probe.package)
        except ImportError:
            # Try common package name transformations
            alt_name = probe.package.replace("-", "_")
            try:
                module = importlib.import_module(alt_name)
            except ImportError:
                raise ImportError(
                    f"Cannot import package '{probe.package}'. "
                    f"Install it or use simulated mode."
                )

        # Navigate to the target function
        func = self._resolve_function(module, probe.function)

        # Call with input data
        if probe.input_data is not None:
            if isinstance(probe.input_data, list):
                return func(*probe.input_data)
            elif isinstance(probe.input_data, dict):
                return func(**probe.input_data)
            else:
                return func(probe.input_data)
        else:
            return func()

    def _resolve_function(self, module: Any, function_path: str) -> Callable:
        """Resolve a dotted function path from a module."""
        parts = function_path.split(".")
        obj = module
        for part in parts:
            obj = getattr(obj, part)
        return obj

    def _check_assertion(self, probe: Probe, actual_output: Any) -> bool:
        """Check whether the probe's assertion holds against actual output."""
        # Check exact output match
        if probe.expected_output is not None:
            if actual_output != probe.expected_output:
                return False

        # Check output has keys
        if probe.output_has_keys is not None:
            if not isinstance(actual_output, dict):
                return False
            for key in probe.output_has_keys:
                if key not in actual_output:
                    return False

        # Check return type
        if probe.returns_type is not None:
            type_map = {
                "dict": dict,
                "list": list,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "tuple": tuple,
                "set": set,
                "None": type(None),
            }
            expected_type = type_map.get(probe.returns_type)
            if expected_type and not isinstance(actual_output, expected_type):
                return False

        # Check raises
        if probe.raises is not None:
            # If we got here without an exception, the probe failed
            return False

        # If no specific assertion, the probe passes if we got output
        return True


class SimulatedProbeRunner(ProbeRunner):
    """Run probes against simulated/historical data instead of live imports.

    Used when the actual package versions are not installed, or for
    testing and demonstration purposes.
    """

    def __init__(self, version_data: Optional[Dict[str, Dict[str, Any]]] = None):
        super().__init__()
        # version_data: {version: {probe_name: output}}
        self.version_data = version_data or {}

    def set_version_data(self, version: str, probe_outputs: Dict[str, Any]):
        """Set the expected output for probes at a specific version."""
        self.version_data[version] = probe_outputs

    def run_probe(self, probe: Probe, package_version: str = "") -> ProbeResult:
        """Run a probe using simulated data."""
        start = time.time()

        if package_version in self.version_data:
            version_data = self.version_data[package_version]
            if probe.name in version_data:
                actual_output = version_data[probe.name]
                elapsed = (time.time() - start) * 1000
                passed = self._check_assertion(probe, actual_output)
                return ProbeResult(
                    probe_name=probe.name,
                    package=probe.package,
                    version=package_version,
                    passed=passed,
                    actual_output=actual_output,
                    execution_time_ms=elapsed,
                )

        # No data for this version — probe fails
        elapsed = (time.time() - start) * 1000
        return ProbeResult(
            probe_name=probe.name,
            package=probe.package,
            version=package_version,
            passed=False,
            error="No simulated data for this version",
            execution_time_ms=elapsed,
        )
