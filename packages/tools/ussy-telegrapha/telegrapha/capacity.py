"""Shannon-Hartley Capacity — Theoretical Throughput Ceiling.

Models pipeline capacity using the Shannon-Hartley theorem:
    C = B * log2(1 + S/N)

Where B = max concurrent operations, S = useful throughput, N = noise rate.
"""

from __future__ import annotations

import math
from typing import Any

from .models import CapacityResult


def compute_snr(signal_rate: float, noise_rate: float) -> float:
    """Compute Signal-to-Noise Ratio."""
    if noise_rate <= 0:
        return float("inf")
    return signal_rate / noise_rate


def compute_shannon_capacity(bandwidth: float, snr: float) -> float:
    """Compute Shannon-Hartley capacity: C = B * log2(1 + S/N)."""
    if snr <= 0:
        return 0.0
    return bandwidth * math.log2(1 + snr)


def compute_utilization(signal_rate: float, capacity: float) -> float:
    """Compute utilization as a percentage of theoretical capacity."""
    if capacity <= 0:
        return 0.0
    return (signal_rate / capacity) * 100.0


def compute_statistical_multiplexing_gain(
    total_bandwidth: float,
    num_workers: int,
    avg_utilization: float,
) -> float:
    """Compute statistical multiplexing gain vs TDM equal partition.

    In TDM, each worker gets B/N bandwidth.
    With statistical multiplexing, workers share the full bandwidth.
    Gain = actual_throughput / (B/N * N * avg_util)
    """
    if num_workers <= 0 or avg_utilization <= 0:
        return 1.0
    # TDM throughput per worker: (B/N) * avg_util
    # Total TDM throughput: B * avg_util
    tdm_throughput = total_bandwidth * avg_utilization
    # With statistical multiplexing, peak throughput approaches B * log2(1 + SNR)
    # Gain is the ratio of statistical multiplexing efficiency to TDM
    # Simplified: gain = 1 / avg_util if we assume bursty traffic
    # More accurate: gain proportional to 1 - (1-avg_util)^N for N independent sources
    if avg_utilization >= 1.0:
        return 1.0
    gain = 1.0 - (1.0 - avg_utilization) ** num_workers
    if tdm_throughput > 0:
        gain = gain / avg_utilization
    return max(1.0, gain)


def analyze_capacity(
    bandwidth: float,
    signal_rate: float,
    noise_rate: float,
    num_workers: int = 1,
    avg_worker_utilization: float | None = None,
) -> CapacityResult:
    """Perform Shannon-Hartley capacity analysis.

    Args:
        bandwidth: Maximum concurrent operations (B_pipeline).
        signal_rate: Useful throughput rate (S_signal).
        noise_rate: Overhead rate (N_noise): retries + health checks + duplicates.
        num_workers: Number of processing workers.
        avg_worker_utilization: Average worker utilization (0.0–1.0), if known.

    Returns:
        CapacityResult with capacity analysis and recommendations.
    """
    snr = compute_snr(signal_rate, noise_rate)
    theoretical_ceiling = compute_shannon_capacity(bandwidth, snr)
    utilization_pct = compute_utilization(signal_rate, theoretical_ceiling)

    multiplexing_gain = 1.0
    if avg_worker_utilization is not None and num_workers > 1:
        multiplexing_gain = compute_statistical_multiplexing_gain(
            bandwidth, num_workers, avg_worker_utilization
        )

    recommendations: list[str] = []

    # Utilization guidance
    if utilization_pct < 40:
        recommendations.append(
            f"Utilization at {utilization_pct:.1f}% of theoretical max — "
            f"consider reducing worker pool size"
        )
        if avg_worker_utilization and num_workers > 1:
            suggested = max(1, int(num_workers * avg_worker_utilization / 0.7))
            recommendations.append(
                f"Workers at {avg_worker_utilization:.0%} avg utilization → "
                f"resize pool from {num_workers} to ~{suggested}"
            )
    elif utilization_pct > 80:
        recommendations.append(
            f"Utilization at {utilization_pct:.1f}% of theoretical max — "
            f"pipeline is near capacity ceiling"
        )
        recommendations.append(
            "Consider increasing bandwidth (more workers) or reducing noise"
        )

    # Noise reduction
    if noise_rate > signal_rate * 0.2:
        recommendations.append(
            f"Noise rate ({noise_rate:.0f} ops/s) is >20% of signal rate — "
            f"investigate retry/duplicate reduction"
        )

    if multiplexing_gain > 1.5:
        recommendations.append(
            f"Statistical multiplexing gain: {multiplexing_gain:.1f}x "
            f"(vs TDM equal partition) — shared capacity is efficient"
        )

    return CapacityResult(
        bandwidth=bandwidth,
        signal_rate=signal_rate,
        noise_rate=noise_rate,
        snr=snr,
        theoretical_ceiling=theoretical_ceiling,
        utilization_pct=utilization_pct,
        multiplexing_gain=round(multiplexing_gain, 2),
        recommendations=recommendations,
    )


def format_capacity_report(result: CapacityResult) -> str:
    """Format capacity result as a human-readable report."""
    lines: list[str] = []

    lines.append("Shannon Capacity Analysis:")
    lines.append(f"  Bandwidth (B): {result.bandwidth:.0f} ops/s (worker pool)")
    lines.append(f"  Signal throughput: {result.signal_rate:.0f} ops/s (successful)")

    if result.noise_rate > 0:
        lines.append(f"  Noise: {result.noise_rate:.0f} ops/s")
    else:
        lines.append("  Noise: 0 ops/s")

    if result.snr == float("inf"):
        lines.append("  SNR: ∞ (no noise)")
    else:
        lines.append(f"  SNR: {result.snr:.2f}")

    lines.append("")
    lines.append(
        f"  Theoretical ceiling: C = {result.bandwidth:.0f} × "
        f"log₂({1 + result.snr:.2f}) = {result.theoretical_ceiling:,.0f} ops/s"
    )
    lines.append(
        f"  Current utilization: {result.signal_rate:,.0f}/{result.theoretical_ceiling:,.0f} "
        f"= {result.utilization_pct:.1f}% of theoretical max"
    )
    lines.append(
        f"  Statistical multiplexing gain: {result.multiplexing_gain:.1f}x "
        f"(vs TDM equal partition)"
    )

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def capacity_to_dict(result: CapacityResult) -> dict[str, Any]:
    """Convert capacity result to a JSON-serializable dictionary."""
    return {
        "bandwidth": result.bandwidth,
        "signal_rate": result.signal_rate,
        "noise_rate": result.noise_rate,
        "snr": round(result.snr, 4) if result.snr != float("inf") else "inf",
        "theoretical_ceiling": round(result.theoretical_ceiling, 2),
        "utilization_pct": round(result.utilization_pct, 2),
        "multiplexing_gain": result.multiplexing_gain,
        "recommendations": result.recommendations,
    }
