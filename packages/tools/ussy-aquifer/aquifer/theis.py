"""
Theis Equation — Transient analysis for time-dependent predictions.

Theis Equation: s = (Q / 4πT) × W(u)
where u = r²S / (4Tt)

Maps to: "How long until this service's performance degrades under sustained load Q?"

s = drawdown (performance degradation)
Q = pumping rate (sustained request rate)
T = transmissivity (cluster total throughput)
S = storage coefficient (queue capacity)
r = radial distance from the "well" (distance in service graph)
t = time since pumping started
W(u) = Theis well function (exponential integral)

This module predicts:
- Time-to-saturation for services under load
- Drawdown at distance from a pumping service
- How adding replicas reduces drawdown
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .topology import ServiceLayer, Topology


def well_function(u: float) -> float:
    """
    Compute the Theis well function W(u) using series approximation.

    W(u) = -0.5772 - ln(u) + u - u²/(2·2!) + u³/(3·3!) - ...

    For small u (< 0.01), use the logarithmic approximation:
    W(u) ≈ -0.5772 - ln(u)

    For larger u, use series expansion with enough terms for convergence.
    """
    if u <= 0:
        return float("inf")
    if u < 1e-10:
        return -0.5772156649 - math.log(u)

    # Series expansion: W(u) = -gamma - ln(u) + sum_{n=1}^{inf} (-1)^{n+1} * u^n / (n * n!)
    result = -0.5772156649 - math.log(u)
    term = u
    for n in range(1, 50):
        sign = 1 if n % 2 == 1 else -1
        factorial_n = math.factorial(n)
        result += sign * (u ** n) / (n * factorial_n)
        if abs(term) < 1e-12:
            break
        term = u**n

    return result


def compute_drawdown(
    Q: float,
    T: float,
    S: float,
    r: float,
    t: float,
) -> float:
    """
    Compute drawdown using the Theis equation.

    s = (Q / (4 * π * T)) * W(u)
    where u = r² * S / (4 * T * t)

    Args:
        Q: Pumping rate (req/s) — the sustained load
        T: Transmissivity (req/s) — cluster total throughput
        S: Storage coefficient (dimensionless) — queue capacity factor
        r: Radial distance from the well (graph distance)
        t: Time since pumping started (seconds)

    Returns:
        Drawdown s (dimensionless head loss)
    """
    if t <= 0 or T <= 0 or S <= 0:
        return 0.0
    if r <= 0:
        r = 0.001  # Avoid division by zero at the well

    u = (r**2 * S) / (4 * T * t)
    W_u = well_function(u)
    s = (Q / (4 * math.pi * T)) * W_u
    return s


def compute_time_to_saturation(
    Q: float,
    T: float,
    S: float,
    r: float,
    saturation_drawdown: float,
) -> Optional[float]:
    """
    Compute time-to-saturation: how long until drawdown reaches a critical level.

    Uses iterative approach to solve the Theis equation for t.

    Args:
        Q: Pumping rate (req/s)
        T: Transmissivity (req/s)
        S: Storage coefficient
        r: Radial distance
        saturation_drawdown: Drawdown level that indicates saturation

    Returns:
        Time in seconds until saturation, or None if never saturates
    """
    if Q <= 0 or T <= 0 or saturation_drawdown <= 0:
        return None

    # Binary search for t
    t_low = 0.01
    t_high = 1e10

    # Check if saturation is ever reached
    s_max = compute_drawdown(Q, T, S, r, t_high)
    if s_max < saturation_drawdown:
        return None  # Never saturates

    # Binary search
    for _ in range(100):
        t_mid = (t_low + t_high) / 2
        s_mid = compute_drawdown(Q, T, S, r, t_mid)
        if s_mid < saturation_drawdown:
            t_low = t_mid
        else:
            t_high = t_mid
        if (t_high - t_low) / max(t_mid, 1e-10) < 1e-8:
            break

    return t_mid


@dataclass
class PredictionResult:
    """Result of a time-dependent prediction."""

    service_name: str
    pumping_rate: float  # Q (req/s)
    transmissivity: float  # T (req/s)
    storage_coefficient: float  # S
    time_seconds: float
    drawdown: float
    is_saturated: bool = False
    saturation_threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.saturation_threshold > 0 and self.drawdown >= self.saturation_threshold:
            self.is_saturated = True


@dataclass
class SystemPrediction:
    """Complete system prediction over time."""

    duration_hours: float
    service_predictions: List[PredictionResult] = field(default_factory=list)
    cascading_failure_services: List[str] = field(default_factory=list)
    time_to_first_saturation: Optional[float] = None

    def summary(self) -> str:
        lines = [
            f"System Prediction (duration: {self.duration_hours}h)",
            f"=" * 50,
        ]
        if self.time_to_first_saturation is not None:
            if self.time_to_first_saturation < 3600:
                time_str = f"{self.time_to_first_saturation:.0f}s"
            elif self.time_to_first_saturation < 86400:
                time_str = f"{self.time_to_first_saturation / 3600:.1f}h"
            else:
                time_str = f"{self.time_to_first_saturation / 86400:.1f}d"
            lines.append(f"First saturation in: {time_str}")
        else:
            lines.append("No saturation predicted within duration")

        if self.cascading_failure_services:
            lines.append(f"\nCascading failure risk: {', '.join(self.cascading_failure_services)}")

        lines.append("\nPer-service predictions:")
        for pred in self.service_predictions:
            status = "⚠ SATURATED" if pred.is_saturated else "✓ OK"
            lines.append(
                f"  {pred.service_name}: drawdown={pred.drawdown:.3f} "
                f"(Q={pred.pumping_rate:.0f}, T={pred.transmissivity:.0f}) {status}"
            )
        return "\n".join(lines)


def predict_system(
    topology: Topology,
    duration_hours: float,
    load_multiplier: float = 1.0,
) -> SystemPrediction:
    """
    Predict system behavior over a duration using the Theis equation.

    For each service, treats its incoming request rate as a "pumping well"
    and computes drawdown over time.

    Args:
        topology: The system topology
        duration_hours: Duration to predict (hours)
        load_multiplier: Scale factor for load (e.g., 2.0 = 2x load)

    Returns:
        SystemPrediction with per-service predictions
    """
    duration_seconds = duration_hours * 3600
    prediction = SystemPrediction(duration_hours=duration_hours)

    first_sat: Optional[float] = None

    for name, svc in topology.services.items():
        # Pumping rate: current queue arrival rate (estimated from downstream flow)
        upstream = topology.get_upstream(name)
        # Estimate Q from upstream services' capacity to send
        Q = 0.0
        for us_name in upstream:
            us = topology.services.get(us_name)
            if us:
                Q += us.effective_K * load_multiplier

        if Q <= 0 and svc.is_recharge:
            Q = svc.effective_K * load_multiplier

        T = svc.transmissivity
        S = svc.specific_storage * 1000  # Scale up for reasonable behavior

        # Compute drawdown at the service location (r=0.001) at duration
        r = 0.001  # At the well
        drawdown = compute_drawdown(Q, T, S, r, duration_seconds)

        # Saturation threshold: when head loss equals available head
        sat_threshold = svc.hydraulic_head if svc.hydraulic_head > 0 else 1.0

        pred = PredictionResult(
            service_name=name,
            pumping_rate=Q,
            transmissivity=T,
            storage_coefficient=S,
            time_seconds=duration_seconds,
            drawdown=drawdown,
            saturation_threshold=sat_threshold,
        )
        prediction.service_predictions.append(pred)

        if pred.is_saturated:
            if first_sat is None:
                first_sat = duration_seconds  # Simplified: saturated at duration
            prediction.cascading_failure_services.append(name)

    prediction.time_to_first_saturation = first_sat

    return prediction
