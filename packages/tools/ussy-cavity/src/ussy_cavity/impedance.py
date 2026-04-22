"""Impedance mismatch analysis for backpressure oscillation.

Models each pipeline stage boundary as an acoustic impedance boundary,
computing reflection/transmission coefficients to identify backpressure
hot-spots and oscillation risks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ussy_cavity.topology import PipelineTopology


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImpedanceBoundary:
    """Impedance analysis at a stage boundary (upstream → downstream)."""

    upstream: str
    downstream: str
    z_upstream: float  # Acoustic impedance of upstream stage
    z_downstream: float  # Acoustic impedance of downstream stage
    reflection_coefficient: float  # R = (Z2-Z1)/(Z2+Z1)
    transmission_coefficient: float  # T = 2*Z2/(Z2+Z1)
    is_mismatch: bool  # |R| > 0.5

    def summary(self) -> str:
        flag = " ⚠ MISMATCH" if self.is_mismatch else ""
        return (
            f"{self.upstream} → {self.downstream}: "
            f"Z₁={self.z_upstream:.1f}, Z₂={self.z_downstream:.1f}, "
            f"R={self.reflection_coefficient:.3f}, T={self.transmission_coefficient:.3f}"
            f"{flag}"
        )


@dataclass
class ImpedanceProfile:
    """Full impedance profile of a pipeline."""

    boundaries: list[ImpedanceBoundary] = field(default_factory=list)
    mismatches: list[ImpedanceBoundary] = field(default_factory=list)
    resonant_cavity_risks: list[tuple[str, str, str]] = field(default_factory=list)
    # (upstream_boundary, downstream_boundary, description)

    def summary(self) -> str:
        lines: list[str] = []
        lines.append(f"Impedance Profile ({len(self.boundaries)} boundaries)")
        lines.append("=" * 60)
        for b in self.boundaries:
            lines.append(b.summary())
        if self.mismatches:
            lines.append("")
            lines.append(f"Mismatch Warnings ({len(self.mismatches)}):")
            for m in self.mismatches:
                lines.append(f"  ⚠ {m.upstream} → {m.downstream}: |R|={abs(m.reflection_coefficient):.3f}")
        if self.resonant_cavity_risks:
            lines.append("")
            lines.append(f"Resonant Cavity Risks ({len(self.resonant_cavity_risks)}):")
            for up, down, desc in self.resonant_cavity_risks:
                lines.append(f"  ⚠ {up} ↔ {down}: {desc}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_stage_impedance(rate: float, buffer_depth: int) -> float:
    """Compute acoustic impedance Z = rate × buffer_depth."""
    return rate * buffer_depth


def compute_reflection_coefficient(z1: float, z2: float) -> float:
    """Reflection coefficient R = (Z2 - Z1) / (Z2 + Z1).

    R ≈ 0  → matched (smooth flow)
    R ≈ 1  → total backpressure reflection
    R ≈ -1 → total negative reflection (rare)
    """
    denom = z1 + z2
    if abs(denom) < 1e-15:
        return 0.0
    return (z2 - z1) / denom


def compute_transmission_coefficient(z1: float, z2: float) -> float:
    """Transmission coefficient T = 2·Z2 / (Z2 + Z1)."""
    denom = z1 + z2
    if abs(denom) < 1e-15:
        return 0.0
    return 2.0 * z2 / denom


def analyze_impedance_mismatches(
    topology: PipelineTopology,
    mismatch_threshold: float = 0.5,
) -> ImpedanceProfile:
    """Analyze impedance mismatches across all pipeline stage boundaries.

    Parameters
    ----------
    topology : PipelineTopology
        The pipeline topology to analyze.
    mismatch_threshold : float
        |R| above this value is flagged as a mismatch (default 0.5).

    Returns
    -------
    ImpedanceProfile
    """
    boundaries: list[ImpedanceBoundary] = []
    mismatches: list[ImpedanceBoundary] = []

    pairs = topology.stage_pairs()

    for upstream, downstream in pairs:
        z_up = topology.stage_impedance(upstream)
        z_down = topology.stage_impedance(downstream)

        R = compute_reflection_coefficient(z_up, z_down)
        T = compute_transmission_coefficient(z_up, z_down)
        is_mismatch = abs(R) > mismatch_threshold

        boundary = ImpedanceBoundary(
            upstream=upstream,
            downstream=downstream,
            z_upstream=z_up,
            z_downstream=z_down,
            reflection_coefficient=R,
            transmission_coefficient=T,
            is_mismatch=is_mismatch,
        )
        boundaries.append(boundary)
        if is_mismatch:
            mismatches.append(boundary)

    # Detect resonant cavity risks: two mismatched boundaries creating
    # a resonant cavity between them (standing wave risk)
    cavity_risks: list[tuple[str, str, str]] = []
    if len(mismatches) >= 2:
        for i in range(len(mismatches)):
            for j in range(i + 1, len(mismatches)):
                b1 = mismatches[i]
                b2 = mismatches[j]
                # Check if they form a cavity (shared node between them)
                if b1.downstream == b2.upstream or b1.upstream == b2.downstream:
                    cavity_stage = b1.downstream if b1.downstream == b2.upstream else b1.upstream
                    desc = (
                        f"Stage '{cavity_stage}' is trapped between two reflective "
                        f"boundaries (R1={abs(b1.reflection_coefficient):.3f}, "
                        f"R2={abs(b2.reflection_coefficient):.3f})"
                    )
                    cavity_risks.append((b1.upstream, b2.downstream, desc))

    return ImpedanceProfile(
        boundaries=boundaries,
        mismatches=mismatches,
        resonant_cavity_risks=cavity_risks,
    )


def recommend_damping(
    topology: PipelineTopology,
    target_zeta: float = 1.0,
) -> list[dict[str, Any]]:
    """Recommend damping adjustments to match impedances.

    For each stage boundary with a mismatch, suggests:
    - Increase buffer (increase Z) for the low-impedance side
    - Decrease rate (decrease Z) for the high-impedance side

    Returns list of recommendation dicts.
    """
    profile = analyze_impedance_mismatches(topology)
    recommendations: list[dict[str, Any]] = []

    for boundary in profile.mismatches:
        rec: dict[str, Any] = {
            "boundary": f"{boundary.upstream} → {boundary.downstream}",
            "reflection_coefficient": boundary.reflection_coefficient,
            "z_upstream": boundary.z_upstream,
            "z_downstream": boundary.z_downstream,
        }

        if boundary.z_downstream < boundary.z_upstream:
            # Downstream is low-Z bottleneck → increase buffer or rate
            stage = topology.stages.get(boundary.downstream)
            if stage:
                # Target Z: match upstream
                target_z = boundary.z_upstream
                current_z = boundary.z_downstream
                if stage.rate > 0:
                    suggested_buffer = int(target_z / stage.rate)
                    rec["recommendation"] = (
                        f"Increase buffer of '{boundary.downstream}' "
                        f"from {stage.buffer} to ~{suggested_buffer} "
                        f"(to match Z={target_z:.0f})"
                    )
                else:
                    rec["recommendation"] = (
                        f"Increase rate of '{boundary.downstream}' "
                        f"to improve impedance match"
                    )
        else:
            # Upstream is low-Z → could rate-limit upstream
            stage = topology.stages.get(boundary.upstream)
            if stage:
                target_z = boundary.z_downstream
                if stage.buffer > 0:
                    suggested_rate = target_z / stage.buffer
                    rec["recommendation"] = (
                        f"Rate-limit '{boundary.upstream}' "
                        f"from {stage.rate:.0f} to ~{suggested_rate:.0f} items/sec "
                        f"(to match Z={target_z:.0f})"
                    )
                else:
                    rec["recommendation"] = (
                        f"Increase buffer of '{boundary.upstream}' "
                        f"to improve impedance match"
                    )

        recommendations.append(rec)

    return recommendations


def format_impedance_profile(profile: ImpedanceProfile) -> str:
    """Format an impedance profile for display."""
    return profile.summary()


def format_recommendations(recommendations: list[dict[str, Any]]) -> str:
    """Format damping recommendations for display."""
    lines: list[str] = []
    if not recommendations:
        lines.append("No impedance mismatches — no damping adjustments needed.")
        return "\n".join(lines)

    lines.append(f"Damping Recommendations ({len(recommendations)})")
    lines.append("=" * 60)
    for rec in recommendations:
        lines.append(f"Boundary: {rec['boundary']}")
        lines.append(f"  R = {rec['reflection_coefficient']:.3f}")
        lines.append(f"  Z_upstream = {rec['z_upstream']:.1f}, Z_downstream = {rec['z_downstream']:.1f}")
        lines.append(f"  → {rec.get('recommendation', 'No specific recommendation')}")
    return "\n".join(lines)
