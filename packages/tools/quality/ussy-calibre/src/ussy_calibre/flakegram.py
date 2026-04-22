"""Flakegram — Otoacoustic Emissions for test suites.

Measures spontaneous test failures (flakiness) and the signal-to-noise ratio
of fault detection vs. flakiness. Computes the growth function α.
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    FlakegramModuleResult,
    FlakegramResult,
    ProjectScan,
)
from ussy_calibre.utils import mean, stdev, psd, linear_regression


class FlakegramAnalyzer:
    """Analyzes test self-noise and fault detection SNR."""

    # Baseline flake rate (industry average ~2%)
    BASELINE_FLAKE_RATE = 0.02
    # SOAE detection threshold in dB
    SOAE_THRESHOLD_DB = 6.0

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(
        self,
        module_flake_data: Optional[dict[str, dict]] = None,
    ) -> FlakegramResult:
        """Compute the Flakegram.

        Args:
            module_flake_data: Optional per-module flake data.
                Keys: module_name, values: dict with:
                  - "pass_fail_series": list of 0/1 (1=pass)
                  - "fault_severities": list of (severity, response) tuples
                  - "flake_rate": float
                If None, heuristic data is computed.
        """
        modules: list[FlakegramModuleResult] = []

        # Gather module names from test modules
        module_names = [
            mod.filepath.split("/")[-1].replace(".py", "").replace("test_", "")
            for mod in self.scan.test_modules
        ]

        if not module_names:
            module_names = ["default"]

        for mod_name in module_names:
            if module_flake_data and mod_name in module_flake_data:
                data = module_flake_data[mod_name]
                result = self._analyze_module_data(mod_name, data)
            else:
                result = self._estimate_module(mod_name)
            modules.append(result)

        result = FlakegramResult(modules=modules)
        return result

    def _analyze_module_data(
        self, module_name: str, data: dict
    ) -> FlakegramModuleResult:
        """Analyze actual flake data for a module."""
        # SOAE from pass/fail series
        series = data.get("pass_fail_series", [])
        flake_rate = data.get("flake_rate", 0.0)

        soae_index = 0.0
        soae_present = False

        if len(series) >= 8:
            # Compute PSD of the series
            psd_vals = psd([float(s) for s in series])
            # Baseline PSD (flat line = no flakiness)
            baseline = psd([mean([float(s) for s in series])] * len(series))
            # SOAE = PSD - baseline at each frequency
            soae_values = [p - b for p, b in zip(psd_vals, baseline)]
            soae_index = max(soae_values) if soae_values else 0.0
            soae_present = soae_index >= self.SOAE_THRESHOLD_DB

        if not soae_present and flake_rate > 0:
            # Fallback: use flake rate directly
            soae_index = 10 * math.log10(max(flake_rate / self.BASELINE_FLAKE_RATE, 1.0))
            soae_present = soae_index >= self.SOAE_THRESHOLD_DB

        # SNR from fault detection data
        fault_data = data.get("fault_severities", [])
        if fault_data:
            severities = [fs[0] for fs in fault_data]
            responses = [fs[1] for fs in fault_data]
            mu_signal = mean(responses)
            sigma_noise = stdev(responses) if len(responses) > 1 else 1.0
            snr_value = mu_signal / sigma_noise if sigma_noise > 0 else 0.0
            # Growth function α
            alpha, _beta = linear_regression(severities, responses)
        else:
            snr_value = 0.0
            alpha = 0.0

        # Classify health
        if alpha < 0.5:
            health = "insensitive"
        elif alpha > 1.5:
            health = "fragile"
        else:
            health = "healthy"

        return FlakegramModuleResult(
            module_name=module_name,
            soae_index=round(soae_index, 2),
            soae_present=soae_present,
            snr_value=round(snr_value, 2),
            growth_alpha=round(alpha, 3),
            health_status=health,
        )

    def _estimate_module(self, module_name: str) -> FlakegramModuleResult:
        """Heuristic flakegram estimate from scan data."""
        # Count integration tests in this module (more integration = more flaky)
        integration_count = 0
        total_count = 0
        for mod in self.scan.test_modules:
            if module_name in mod.filepath or module_name == "default":
                for func in mod.functions:
                    total_count += 1
                    if func.test_type == "integration":
                        integration_count += 1

        # Estimate flake rate
        base_rate = self.BASELINE_FLAKE_RATE
        integration_factor = integration_count / max(total_count, 1)
        estimated_rate = base_rate + 0.15 * integration_factor

        soae_index = 10 * math.log10(max(estimated_rate / self.BASELINE_FLAKE_RATE, 1.0))
        soae_present = soae_index >= self.SOAE_THRESHOLD_DB

        # Estimate SNR
        snr_value = max(1.0, 5.0 - 3.0 * integration_factor)

        # Estimate alpha (healthy default)
        alpha = 1.0 - 0.3 * integration_factor

        health = "healthy"
        if alpha < 0.5:
            health = "insensitive"
        elif alpha > 1.5:
            health = "fragile"

        return FlakegramModuleResult(
            module_name=module_name,
            soae_index=round(soae_index, 2),
            soae_present=soae_present,
            snr_value=round(snr_value, 2),
            growth_alpha=round(alpha, 3),
            health_status=health,
        )


def run_flakegram(
    project_path: str,
    module_flake_data: Optional[dict[str, dict]] = None,
) -> FlakegramResult:
    """Convenience entry point for Flakegram analysis."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = FlakegramAnalyzer(scan)
    return analyzer.analyze(module_flake_data=module_flake_data)
