"""Full report generation combining all analyses.

Generates a comprehensive resonance spectrum report that includes:
- Natural frequency (mode) analysis
- Impedance profile
- Standing wave detection
- Beat frequency (livelock) detection
- Damping recommendations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cavity.beat_frequency import BeatFrequency, detect_livelock, format_beat_frequencies
from cavity.damping import DampingResult, analyze_stage_damping, format_damping_results
from cavity.impedance import (
    ImpedanceProfile,
    analyze_impedance_mismatches,
    format_impedance_profile,
    format_recommendations,
    recommend_damping,
)
from cavity.modes import ResonanceMode, format_modes, predict_deadlocks
from cavity.standing_wave import StandingWave, detect_standing_waves, format_standing_waves
from cavity.topology import PipelineTopology


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CavityReport:
    """Comprehensive resonance analysis report."""

    timestamp: str
    pipeline_name: str = ""
    modes: list[ResonanceMode] | None = None
    impedance: ImpedanceProfile | None = None
    standing_waves: list[StandingWave] | None = None
    beat_frequencies: list[BeatFrequency] | None = None
    damping: list[DampingResult] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "pipeline_name": self.pipeline_name,
        }

        if self.modes is not None:
            result["modes"] = [
                {
                    "index": m.index,
                    "frequency": m.frequency,
                    "damping_ratio": m.damping_ratio,
                    "risk_level": m.risk_level.value,
                    "q_factor": m.q_factor if m.q_factor < 1e6 else "inf",
                    "involved_nodes": m.involved_nodes,
                }
                for m in self.modes
            ]

        if self.impedance is not None:
            result["impedance"] = {
                "boundaries": [
                    {
                        "upstream": b.upstream,
                        "downstream": b.downstream,
                        "z_upstream": b.z_upstream,
                        "z_downstream": b.z_downstream,
                        "reflection_coefficient": b.reflection_coefficient,
                        "transmission_coefficient": b.transmission_coefficient,
                        "is_mismatch": b.is_mismatch,
                    }
                    for b in self.impedance.boundaries
                ],
                "mismatches": len(self.impedance.mismatches),
                "resonant_cavity_risks": len(self.impedance.resonant_cavity_risks),
            }

        if self.standing_waves is not None:
            result["standing_waves"] = [
                {
                    "frequency": w.frequency,
                    "amplitude": w.amplitude,
                    "persistence": w.persistence,
                    "q_factor": w.q_factor if w.q_factor < 1e6 else "inf",
                }
                for w in self.standing_waves
            ]

        if self.beat_frequencies is not None:
            result["beat_frequencies"] = [
                {
                    "beat_frequency": b.beat_frequency,
                    "beat_period": b.beat_period,
                    "f1": b.f1,
                    "f2": b.f2,
                    "amplitude": b.amplitude,
                    "is_livelock": b.is_livelock,
                    "avg_throughput": b.avg_throughput,
                }
                for b in self.beat_frequencies
            ]

        if self.damping is not None:
            result["damping"] = [
                {
                    "stage": d.stage_name,
                    "zeta": d.zeta,
                    "damping_class": d.damping_class.value,
                    "recommendation": d.recommendation,
                }
                for d in self.damping
            ]

        return result

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_text(self) -> str:
        """Format report as human-readable text."""
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("CAVITY — Acoustic Resonance Analysis Report")
        lines.append("=" * 70)
        lines.append(f"Generated: {self.timestamp}")
        if self.pipeline_name:
            lines.append(f"Pipeline: {self.pipeline_name}")
        lines.append("")

        if self.modes is not None:
            lines.append(format_modes(self.modes))
            lines.append("")

        if self.impedance is not None:
            lines.append(format_impedance_profile(self.impedance))
            lines.append("")

        if self.standing_waves is not None:
            lines.append(format_standing_waves(self.standing_waves))
            lines.append("")

        if self.beat_frequencies is not None:
            lines.append(format_beat_frequencies(self.beat_frequencies))
            lines.append("")

        if self.damping is not None:
            lines.append(format_damping_results(self.damping))
            lines.append("")

        lines.append("=" * 70)
        lines.append("End of Report")
        lines.append("=" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    topology: PipelineTopology,
    wait_time_series: list[float] | None = None,
    throughput_series: list[float] | None = None,
    fs: float = 1.0,
    target_zeta: float = 1.0,
    pipeline_name: str = "",
) -> CavityReport:
    """Generate a full resonance analysis report.

    Parameters
    ----------
    topology : PipelineTopology
        The pipeline topology.
    wait_time_series : list[float] or None
        Wait duration time series for standing wave / livelock detection.
    throughput_series : list[float] or None
        Throughput time series for livelock confirmation.
    fs : float
        Sampling frequency of the time series (Hz).
    target_zeta : float
        Target damping ratio for recommendations.
    pipeline_name : str
        Name for the report header.

    Returns
    -------
    CavityReport
    """
    import numpy as np

    # Mode analysis
    adj = topology.adjacency_matrix
    node_names = topology.node_names
    modes = predict_deadlocks(adj, node_names)

    # Impedance analysis
    impedance = analyze_impedance_mismatches(topology)

    # Damping analysis
    damping = analyze_stage_damping(topology, target_zeta)

    # Standing wave detection (requires time series)
    standing_waves = None
    beat_frequencies = None
    if wait_time_series is not None and len(wait_time_series) > 0:
        signal = np.array(wait_time_series, dtype=float)
        standing_waves = detect_standing_waves(signal, fs=fs)

        throughput = np.array(throughput_series, dtype=float) if throughput_series else None
        beat_frequencies = detect_livelock(signal, throughput, fs=fs)

    return CavityReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_name=pipeline_name,
        modes=modes,
        impedance=impedance,
        standing_waves=standing_waves,
        beat_frequencies=beat_frequencies,
        damping=damping,
    )
