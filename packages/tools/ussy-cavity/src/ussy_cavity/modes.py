"""Resonance mode analysis via eigenvalue decomposition.

Computes the natural frequencies and damping ratios of a pipeline topology
by treating the adjacency matrix as a resonant cavity and decomposing it
into its eigenmodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class RiskLevel(Enum):
    """Risk level of a resonance mode."""

    UNDAMPED = "UNDAMPED"
    UNDERDAMPED = "UNDERDAMPED"
    CRITICALLY_DAMPED = "CRITICALLY_DAMPED"
    OVERDAMPED = "OVERDAMPED"


@dataclass
class ResonanceMode:
    """A single resonance mode of the pipeline cavity."""

    index: int
    frequency: float  # Natural frequency (Hz)
    damping_ratio: float  # ζ
    risk_level: RiskLevel
    eigenvalue: complex
    eigenvector: np.ndarray
    involved_nodes: list[str] = field(default_factory=list)

    @property
    def q_factor(self) -> float:
        """Q-factor = 1 / (2ζ).  High Q → persistent deadlock."""
        if self.damping_ratio < 1e-12:
            return float("inf")
        return 1.0 / (2.0 * self.damping_ratio)

    def summary(self) -> str:
        risk = self.risk_level.value
        q = f"{self.q_factor:.1f}" if self.q_factor < 1e6 else "∞"
        return (
            f"Mode {self.index}: f={self.frequency:.4f}Hz, "
            f"ζ={self.damping_ratio:.4f} ({risk}), Q={q}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

# Thresholds for classification
_UNDAMPED_THRESHOLD = 0.05
_UNDERDAMPED_THRESHOLD = 1.0
_CRITICAL_TOLERANCE = 0.05


def classify_damping(zeta: float) -> RiskLevel:
    """Classify a damping ratio into a risk level."""
    if zeta < _UNDAMPED_THRESHOLD:
        return RiskLevel.UNDAMPED
    if zeta < _UNDERDAMPED_THRESHOLD - _CRITICAL_TOLERANCE:
        return RiskLevel.UNDERDAMPED
    if zeta < _UNDERDAMPED_THRESHOLD + _CRITICAL_TOLERANCE:
        return RiskLevel.CRITICALLY_DAMPED
    return RiskLevel.OVERDAMPED


def compute_natural_frequencies(
    adjacency_matrix: np.ndarray,
    node_names: list[str] | None = None,
    dt: float = 1.0,
) -> list[ResonanceMode]:
    """Compute natural frequencies from the adjacency matrix eigenvalues.

    Parameters
    ----------
    adjacency_matrix : np.ndarray
        N×N adjacency matrix of the pipeline graph.
    node_names : list[str] or None
        Human-readable names for each node index.
    dt : float
        Time step used in the frequency calculation (default 1.0s).

    Returns
    -------
    list[ResonanceMode]
        Modes sorted by risk (undamped first), then by frequency.
    """
    n = adjacency_matrix.shape[0]
    if n == 0:
        return []

    eigenvalues, eigenvectors = np.linalg.eig(adjacency_matrix)

    modes: list[ResonanceMode] = []
    for i, lam in enumerate(eigenvalues):
        magnitude = abs(lam)
        frequency = magnitude / (2.0 * np.pi * dt) if magnitude > 1e-15 else 0.0

        if magnitude > 1e-15:
            damping_ratio = max(-lam.real, 0.0) / magnitude
        else:
            damping_ratio = 0.0

        # Clamp negative damping to zero (we only care about positive real parts
        # for growing modes; negative damping_ratio would mean growing oscillation)
        damping_ratio = max(damping_ratio, 0.0)

        risk = classify_damping(damping_ratio)

        # Determine involved nodes from eigenvector
        vec = eigenvectors[:, i]
        involved: list[str] = []
        if node_names:
            threshold = 0.1 * np.max(np.abs(vec))
            for j, name in enumerate(node_names):
                if abs(vec[j]) > threshold:
                    involved.append(name)

        modes.append(
            ResonanceMode(
                index=i,
                frequency=frequency,
                damping_ratio=damping_ratio,
                risk_level=risk,
                eigenvalue=lam,
                eigenvector=vec,
                involved_nodes=involved,
            )
        )

    # Sort: undamped first, then underdamped, then by frequency descending
    risk_order = {
        RiskLevel.UNDAMPED: 0,
        RiskLevel.UNDERDAMPED: 1,
        RiskLevel.CRITICALLY_DAMPED: 2,
        RiskLevel.OVERDAMPED: 3,
    }
    modes.sort(key=lambda m: (risk_order[m.risk_level], -m.frequency))
    return modes


def predict_deadlocks(
    adjacency_matrix: np.ndarray,
    node_names: list[str] | None = None,
    dt: float = 1.0,
    max_risk: RiskLevel | None = None,
) -> list[ResonanceMode]:
    """Predict potential deadlocks from pipeline topology.

    Returns modes that represent deadlock risk (undamped or underdamped).
    If *max_risk* is given, only return modes at or below that risk level.
    """
    modes = compute_natural_frequencies(adjacency_matrix, node_names, dt)

    risk_cutoff = {
        RiskLevel.UNDAMPED: {RiskLevel.UNDAMPED},
        RiskLevel.UNDERDAMPED: {RiskLevel.UNDAMPED, RiskLevel.UNDERDAMPED},
        RiskLevel.CRITICALLY_DAMPED: {
            RiskLevel.UNDAMPED,
            RiskLevel.UNDERDAMPED,
            RiskLevel.CRITICALLY_DAMPED,
        },
        RiskLevel.OVERDAMPED: {
            RiskLevel.UNDAMPED,
            RiskLevel.UNDERDAMPED,
            RiskLevel.CRITICALLY_DAMPED,
            RiskLevel.OVERDAMPED,
        },
    }

    if max_risk is not None:
        allowed = risk_cutoff.get(max_risk, set())
        modes = [m for m in modes if m.risk_level in allowed]
    else:
        # By default return undamped and underdamped (deadlock-relevant)
        modes = [m for m in modes if m.risk_level in {RiskLevel.UNDAMPED, RiskLevel.UNDERDAMPED}]

    return modes


def format_modes(modes: list[ResonanceMode]) -> str:
    """Format modes into a human-readable string."""
    lines: list[str] = []
    if not modes:
        lines.append("No resonance modes detected.")
        return "\n".join(lines)

    lines.append(f"Resonance Modes ({len(modes)} found)")
    lines.append("=" * 60)
    for mode in modes:
        lines.append(mode.summary())
        if mode.involved_nodes:
            lines.append(f"  Involved: {' → '.join(mode.involved_nodes)}")
    return "\n".join(lines)
