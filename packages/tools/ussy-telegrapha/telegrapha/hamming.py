"""Hamming Analysis — FEC vs ARQ Decision Framework.

Provides a formal framework for deciding between:
- ARQ (Automatic Repeat reQuest): retry on failure
- FEC (Forward Error Correction): redundant processing with K-of-N acceptance

Also computes schema drift distance (Hamming distance for messages).
"""

from __future__ import annotations

import math
from typing import Any

from .models import HammingResult


def compute_arq_metrics(
    error_rate: float,
    pipeline_length: int,
) -> tuple[float, float, float]:
    """Compute ARQ (retry) metrics.

    Args:
        error_rate: Per-hop error probability.
        pipeline_length: Number of hops.

    Returns:
        Tuple of (expected_transmissions_per_hop, total_latency_factor, bandwidth_overhead_pct)
    """
    if error_rate >= 1.0:
        return (float("inf"), float("inf"), 100.0)

    # Expected transmissions per hop = 1 / (1 - error_rate)
    expected_transmissions = 1.0 / (1.0 - error_rate)

    # Total latency factor = pipeline_length * expected_transmissions
    total_latency = pipeline_length * expected_transmissions

    # Bandwidth overhead = only on errors
    bandwidth_overhead = error_rate * 100  # percentage

    return (expected_transmissions, total_latency, bandwidth_overhead)


def compute_fec_metrics(
    error_rate: float,
    code_n: int,
    code_k: int,
) -> tuple[float, float, float]:
    """Compute FEC (redundant processing) metrics.

    For an (n, k) code: process n times, accept k-of-n agreements.
    P_failure = sum(C(n,j) * p^j * (1-p)^(n-j) for j=0 to n-k)

    Args:
        error_rate: Per-hop error probability.
        code_n: Total number of redundant copies.
        code_k: Minimum agreements needed.

    Returns:
        Tuple of (failure_probability, latency_factor, bandwidth_overhead_pct)
    """
    # P(failure) = probability that fewer than k out of n succeed
    # = sum(C(n,j) * (1-p)^j * p^(n-j) for j=0 to k-1)
    # where p = error_rate, j = number of successes
    p_fail = 0.0
    for j in range(code_k):
        # j successes, (n-j) failures
        p_fail += math.comb(code_n, j) * ((1 - error_rate) ** j) * (error_rate ** (code_n - j))

    # Latency factor: always process n times
    latency_factor = float(code_n)

    # Bandwidth overhead: (n/k - 1) * 100%
    bandwidth_overhead = ((code_n / code_k) - 1.0) * 100.0

    return (p_fail, latency_factor, bandwidth_overhead)


def compute_break_even_error_rate(
    code_n: int,
    code_k: int,
    target_reliability: float,
) -> float:
    """Find the break-even error rate where FEC becomes preferred over ARQ.

    This is the error rate at which FEC's failure probability equals
    the target reliability threshold.
    """
    # Binary search for break-even point
    lo, hi = 0.0, 1.0
    for _ in range(100):  # Binary search iterations
        mid = (lo + hi) / 2.0
        p_fail, _, bw_overhead = compute_fec_metrics(mid, code_n, code_k)
        arq_expected, _, arq_bw = compute_arq_metrics(mid, 1)

        # FEC preferred when error rate is high enough that
        # bandwidth cost of ARQ exceeds FEC
        if arq_bw > bw_overhead:
            hi = mid
        else:
            lo = mid

    return lo


def compute_hamming_distance(
    schema_a: list[str],
    schema_b: list[str],
) -> int:
    """Compute Hamming distance between two schemas (field lists).

    Counts the number of fields that differ between the two schemas.
    """
    set_a = set(schema_a)
    set_b = set(schema_b)

    # Fields only in A + fields only in B
    distance = len(set_a.symmetric_difference(set_b))
    return distance


def compute_correction_capacity(min_distance: int) -> int:
    """Compute error correction capacity from minimum Hamming distance.

    t = floor((d_min - 1) / 2)
    """
    return (min_distance - 1) // 2


def analyze_hamming(
    error_rate: float,
    pipeline_length: int,
    target_reliability: float = 0.999,
    fec_code_n: int = 3,
    fec_code_k: int = 2,
    schema_drift_distance: int = 0,
    min_hamming_distance: int = 3,
) -> HammingResult:
    """Perform full FEC vs ARQ decision analysis.

    Args:
        error_rate: Per-hop error probability.
        pipeline_length: Number of hops in the pipeline.
        target_reliability: Target end-to-end reliability.
        fec_code_n: FEC code total copies.
        fec_code_k: FEC code minimum agreements.
        schema_drift_distance: Current Hamming distance between producer/consumer schemas.
        min_hamming_distance: Minimum Hamming distance of the schema code.

    Returns:
        HammingResult with decision analysis and recommendations.
    """
    # ARQ metrics
    arq_expected, arq_latency, arq_bw = compute_arq_metrics(
        error_rate, pipeline_length
    )

    # FEC metrics
    fec_failure, fec_latency, fec_bw = compute_fec_metrics(
        error_rate, fec_code_n, fec_code_k
    )

    # Break-even point
    break_even = compute_break_even_error_rate(
        fec_code_n, fec_code_k, target_reliability
    )

    # Decision: prefer ARQ at low error rates, FEC at high error rates
    if error_rate < break_even:
        preferred = "ARQ"
    else:
        preferred = "FEC"

    # Correction capacity
    correction_cap = compute_correction_capacity(min_hamming_distance)

    # Recommendations
    recommendations: list[str] = []

    if preferred == "ARQ":
        recommendations.append(
            f"ARQ preferred (P_error is low, bandwidth savings dominate)"
        )
        recommendations.append(
            f"Break-even: if P_error > {break_even:.0%}, switch to FEC ({fec_code_n},{fec_code_k})"
        )
    else:
        recommendations.append(
            f"FEC preferred (high error rate, redundant processing more efficient)"
        )

    if schema_drift_distance > 0:
        if schema_drift_distance >= min_hamming_distance:
            recommendations.append(
                f"CRITICAL: schema drift distance ({schema_drift_distance}) "
                f">= d_min ({min_hamming_distance}) — cannot detect all drifts"
            )
        elif schema_drift_distance > correction_cap:
            recommendations.append(
                f"WARNING: schema drift at correction limit "
                f"(distance={schema_drift_distance}, capacity={correction_cap})"
            )
        else:
            recommendations.append(
                f"Schema drift within correction capacity "
                f"(distance={schema_drift_distance}, capacity={correction_cap})"
            )

    return HammingResult(
        error_rate=error_rate,
        pipeline_length=pipeline_length,
        target_reliability=target_reliability,
        arq_expected_transmissions=arq_expected,
        arq_latency_factor=arq_latency,
        arq_bandwidth_overhead=arq_bw,
        fec_code_n=fec_code_n,
        fec_code_k=fec_code_k,
        fec_failure_prob=fec_failure,
        fec_latency_factor=fec_latency,
        fec_bandwidth_overhead=fec_bw,
        preferred=preferred,
        break_even_error_rate=break_even,
        schema_drift_distance=schema_drift_distance,
        correction_capacity=correction_cap,
        recommendations=recommendations,
    )


def format_hamming_report(result: HammingResult) -> str:
    """Format Hamming analysis result as a human-readable report."""
    lines: list[str] = []

    lines.append("FEC vs ARQ Analysis:")
    lines.append("")
    lines.append(f"  Per-hop error rate: {result.error_rate:.1%}")
    lines.append(f"  Pipeline length: {result.pipeline_length} hops")
    lines.append(f"  Target reliability: {result.target_reliability:.1%}")
    lines.append("")

    lines.append("  ARQ (retry):")
    lines.append(
        f"    Expected transmissions: 1/(1-{result.error_rate}) = "
        f"{result.arq_expected_transmissions:.3f} per hop"
    )
    lines.append(
        f"    Total latency overhead: {result.pipeline_length} × "
        f"{result.arq_expected_transmissions:.3f} × T_base = "
        f"{result.arq_latency_factor:.2f} × T_base"
    )
    lines.append(
        f"    Bandwidth cost: {result.arq_bandwidth_overhead:.1f}% overhead (only on errors)"
    )
    lines.append("")

    lines.append(f"  FEC (redundant processing):")
    lines.append(
        f"    ({result.fec_code_n},{result.fec_code_k}) code: "
        f"process {result.fec_code_n}×, accept {result.fec_code_k}-of-{result.fec_code_n} agreements"
    )
    lines.append(
        f"    P_failure = {result.fec_failure_prob:.4%}"
    )
    lines.append(
        f"    Total latency: {result.fec_latency_factor:.0f} × T_base (always, even when no errors)"
    )
    lines.append(
        f"    Bandwidth cost: {result.fec_bandwidth_overhead:.0f}% overhead (always)"
    )
    lines.append("")

    lines.append(
        f"  Decision: {result.preferred} preferred"
    )
    lines.append(
        f"  Break-even: if P_error > {result.break_even_error_rate:.0%}, "
        f"switch to FEC ({result.fec_code_n},{result.fec_code_k})"
    )

    if result.schema_drift_distance > 0:
        lines.append("")
        lines.append("  Schema drift distance (Hamming distance for messages):")
        lines.append(
            f"    Current: {result.schema_drift_distance} fields differ "
            f"between producer/consumer schemas"
        )
        lines.append(
            f"    Correction capacity: d_min=3 → "
            f"corrects {result.correction_capacity} field drift, "
            f"detects {result.correction_capacity * 2}"
        )
        if result.schema_drift_distance > result.correction_capacity:
            lines.append("    → WARNING: schema drift at correction limit")

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def hamming_to_dict(result: HammingResult) -> dict[str, Any]:
    """Convert Hamming analysis result to a JSON-serializable dictionary."""
    return {
        "error_rate": result.error_rate,
        "pipeline_length": result.pipeline_length,
        "target_reliability": result.target_reliability,
        "arq": {
            "expected_transmissions": round(result.arq_expected_transmissions, 6),
            "latency_factor": round(result.arq_latency_factor, 4),
            "bandwidth_overhead_pct": round(result.arq_bandwidth_overhead, 2),
        },
        "fec": {
            "code_n": result.fec_code_n,
            "code_k": result.fec_code_k,
            "failure_prob": result.fec_failure_prob,
            "latency_factor": result.fec_latency_factor,
            "bandwidth_overhead_pct": round(result.fec_bandwidth_overhead, 2),
        },
        "preferred": result.preferred,
        "break_even_error_rate": round(result.break_even_error_rate, 4),
        "schema_drift_distance": result.schema_drift_distance,
        "correction_capacity": result.correction_capacity,
        "recommendations": result.recommendations,
    }
