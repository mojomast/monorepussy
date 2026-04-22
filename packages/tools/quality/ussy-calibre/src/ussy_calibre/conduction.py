"""Conduction Study — ABR for test suites.

Measures latency and signal preservation through test chain stages
(unit → service → integration), detecting bottlenecks and signal loss.
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    ConductionResult,
    ConductionStage,
    ProjectScan,
)
from ussy_calibre.utils import mean, stdev


class ConductionAnalyzer:
    """Analyzes test chain conduction (latency + signal preservation)."""

    # Fsp threshold: below 2.5 means stage response is noise
    FSP_THRESHOLD = 2.5
    # V/I ratio thresholds
    VI_LOSS_THRESHOLD = 0.5
    VI_AMPLIFY_THRESHOLD = 2.0

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(
        self,
        stage_data: Optional[list[dict]] = None,
    ) -> ConductionResult:
        """Compute the conduction study.

        Args:
            stage_data: Optional list of stage dicts with keys:
                name, stage_type, latency_ms, latency_samples (list[float]),
                assertion_count, code_covered_pct.
                If None, heuristic data is computed.
        """
        if stage_data is not None:
            stages = [
                ConductionStage(
                    name=s["name"],
                    stage_type=s["stage_type"],
                    latency_ms=s["latency_ms"],
                    assertion_count=s["assertion_count"],
                    code_covered_pct=s["code_covered_pct"],
                )
                for s in stage_data
            ]
            latency_samples = {
                s["name"]: s.get("latency_samples", [s["latency_ms"]])
                for s in stage_data
            }
        else:
            stages, latency_samples = self._estimate_stages()

        if not stages:
            return ConductionResult()

        # Compute interstage latencies
        interstage_latencies = []
        for i in range(1, len(stages)):
            ict = stages[i].latency_ms - stages[i - 1].latency_ms
            interstage_latencies.append(round(ict, 2))

        # Compute Fsp values
        fsp_values: dict[str, float] = {}
        for stage in stages:
            samples = latency_samples.get(stage.name, [stage.latency_ms])
            mu = mean(samples)
            sigma = stdev(samples)
            fsp = mu / sigma if sigma > 0 else float("inf")
            fsp_values[stage.name] = round(fsp, 2)

        # Compute V/I ratio (output assertions / input assertions)
        input_assertions = stages[0].assertion_count if stages else 0
        output_assertions = stages[-1].assertion_count if stages else 0
        vi_ratio = output_assertions / input_assertions if input_assertions > 0 else 0.0

        # Find bottleneck (stage with highest interstage latency)
        bottleneck = None
        if interstage_latencies:
            max_ict_idx = interstage_latencies.index(max(interstage_latencies))
            bottleneck = stages[max_ict_idx + 1].name

        return ConductionResult(
            stages=stages,
            interstage_latencies=interstage_latencies,
            fsp_values=fsp_values,
            vi_ratio=round(vi_ratio, 3),
            bottleneck_stage=bottleneck,
        )

    def _estimate_stages(
        self,
    ) -> tuple[list[ConductionStage], dict[str, list[float]]]:
        """Heuristic stage estimation from scan data."""
        # Count functions by type
        unit_funcs = []
        service_funcs = []
        integration_funcs = []

        for mod in self.scan.test_modules:
            for func in mod.functions:
                if func.test_type == "unit":
                    unit_funcs.append(func)
                elif func.test_type == "integration":
                    integration_funcs.append(func)
                else:
                    # Default unclassified tests as service-level
                    service_funcs.append(func)

        # Build stages with estimated latencies
        stages = []
        latency_samples = {}

        # Stage I: Unit tests (fast)
        unit_latency = 5.0 + len(unit_funcs) * 0.5
        stages.append(
            ConductionStage(
                name="Wave_I_Unit",
                stage_type="unit",
                latency_ms=round(unit_latency, 1),
                assertion_count=max(1, len(unit_funcs)),
                code_covered_pct=round(min(95.0, 40.0 + len(unit_funcs) * 2), 1),
            )
        )
        latency_samples["Wave_I_Unit"] = [
            unit_latency + (i % 3 - 1) * 0.3 for i in range(5)
        ]

        # Stage III: Service tests (medium)
        if service_funcs:
            service_latency = unit_latency + 15.0 + len(service_funcs) * 2.0
            stages.append(
                ConductionStage(
                    name="Wave_III_Service",
                    stage_type="service",
                    latency_ms=round(service_latency, 1),
                    assertion_count=max(1, len(service_funcs)),
                    code_covered_pct=round(min(85.0, 30.0 + len(service_funcs) * 3), 1),
                )
            )
            latency_samples["Wave_III_Service"] = [
                service_latency + (i % 4 - 2) * 1.0 for i in range(5)
            ]

        # Stage V: Integration tests (slow)
        if integration_funcs:
            int_latency = (
                (stages[-1].latency_ms if stages else unit_latency)
                + 30.0
                + len(integration_funcs) * 5.0
            )
            stages.append(
                ConductionStage(
                    name="Wave_V_Integration",
                    stage_type="integration",
                    latency_ms=round(int_latency, 1),
                    assertion_count=max(1, len(integration_funcs)),
                    code_covered_pct=round(min(70.0, 20.0 + len(integration_funcs) * 4), 1),
                )
            )
            latency_samples["Wave_V_Integration"] = [
                int_latency + (i % 5 - 2) * 2.0 for i in range(5)
            ]

        if not stages:
            # Default minimal stage
            stages.append(
                ConductionStage(
                    name="Wave_I_Unit",
                    stage_type="unit",
                    latency_ms=10.0,
                    assertion_count=1,
                    code_covered_pct=50.0,
                )
            )
            latency_samples["Wave_I_Unit"] = [10.0] * 5

        return stages, latency_samples


def run_conduction(
    project_path: str,
    stage_data: Optional[list[dict]] = None,
) -> ConductionResult:
    """Convenience entry point for Conduction study."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = ConductionAnalyzer(scan)
    return analyzer.analyze(stage_data=stage_data)
