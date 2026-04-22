"""Dashboard — Aggregate view of all pipeline analyses."""

from __future__ import annotations

import json
from typing import Any

from .models import PipelineTopology
from .attenuation import analyze_attenuation, attenuation_to_dict
from .relay_chain import analyze_relay_chain, relay_chain_to_dict
from .capacity import analyze_capacity, capacity_to_dict
from .hamming import analyze_hamming, hamming_to_dict
from .dlo import analyze_dlo, dlo_to_dict, load_dlq_entries
from .topology import load_topology


def generate_dashboard(
    topology: PipelineTopology,
    target_sla: float = 0.999,
    bandwidth: float = 500.0,
    signal_rate: float = 420.0,
    noise_rate: float = 80.0,
    error_rate: float = 0.03,
    dlq_path: str | None = None,
    dlq_accumulation_rate: float | None = None,
    dlq_resolution_rate: float | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive dashboard combining all analyses.

    Args:
        topology: Pipeline topology to analyze.
        target_sla: Target end-to-end SLA.
        bandwidth: Pipeline bandwidth (ops/s).
        signal_rate: Signal throughput rate.
        noise_rate: Noise rate.
        error_rate: Per-hop error rate for Hamming analysis.
        dlq_path: Path to DLQ entries JSON file.
        dlq_accumulation_rate: DLQ accumulation rate.
        dlq_resolution_rate: DLQ resolution rate.

    Returns:
        Dictionary with all analysis results.
    """
    dashboard: dict[str, Any] = {
        "topology": topology.name,
        "routes": [],
        "capacity": None,
        "hamming": None,
        "dlo": None,
    }

    # Analyze each route
    for route in topology.routes:
        route_analysis: dict[str, Any] = {
            "name": route.name,
            "attenuation": attenuation_to_dict(analyze_attenuation(route)),
            "relay_chain": relay_chain_to_dict(
                analyze_relay_chain(route, target_sla=target_sla)
            ),
        }
        dashboard["routes"].append(route_analysis)

    # Capacity analysis
    cap_result = analyze_capacity(bandwidth, signal_rate, noise_rate)
    dashboard["capacity"] = capacity_to_dict(cap_result)

    # Hamming analysis
    pipeline_length = 0
    for route in topology.routes:
        pipeline_length = max(pipeline_length, route.hop_count)
    if pipeline_length == 0:
        pipeline_length = 1

    hamming_result = analyze_hamming(error_rate, pipeline_length)
    dashboard["hamming"] = hamming_to_dict(hamming_result)

    # DLO analysis
    if dlq_path:
        try:
            entries = load_dlq_entries(dlq_path)
            dlo_result = analyze_dlo(
                entries,
                accumulation_rate=dlq_accumulation_rate,
                resolution_rate=dlq_resolution_rate,
            )
            dashboard["dlo"] = dlo_to_dict(dlo_result)
        except (FileNotFoundError, json.JSONDecodeError):
            dashboard["dlo"] = None

    return dashboard


def format_dashboard_report(dashboard: dict[str, Any]) -> str:
    """Format dashboard as a human-readable report."""
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append(f"TELEGRAPHA DASHBOARD — {dashboard['topology']}")
    lines.append("=" * 60)

    # Routes
    for route in dashboard.get("routes", []):
        lines.append("")
        lines.append(f"Route: {route['name']}")
        lines.append("-" * 40)

        att = route.get("attenuation", {})
        if att:
            lines.append(
                f"  Fidelity: {att.get('fidelity', 'N/A'):.3f} "
                f"({att.get('cumulative_degradation', 0) * 100:.1f}% degradation)"
            )
            lines.append(
                f"  Distortionless: {'Yes' if att.get('is_distortionless') else 'No'}"
            )

        rc = route.get("relay_chain", {})
        if rc:
            lines.append(
                f"  Reliability: {rc.get('actual_reliability', 0):.4%} "
                f"({'meets' if rc.get('meets_sla') else 'below'} SLA)"
            )

    # Capacity
    cap = dashboard.get("capacity")
    if cap:
        lines.append("")
        lines.append("Capacity:")
        lines.append(f"  Theoretical ceiling: {cap.get('theoretical_ceiling', 0):,.0f} ops/s")
        lines.append(f"  Utilization: {cap.get('utilization_pct', 0):.1f}%")

    # Hamming
    ham = dashboard.get("hamming")
    if ham:
        lines.append("")
        lines.append("FEC vs ARQ:")
        lines.append(f"  Preferred: {ham.get('preferred', 'N/A')}")
        lines.append(f"  Break-even error rate: {ham.get('break_even_error_rate', 0):.1%}")

    # DLO
    dlo = dashboard.get("dlo")
    if dlo:
        lines.append("")
        lines.append("Dead Letter Office:")
        lines.append(f"  Health: {dlo.get('health_score', 0):.2f} ({dlo.get('health_status', 'N/A')})")
        lines.append(f"  Churn rate: {dlo.get('churn_rate', 0):.2f}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
