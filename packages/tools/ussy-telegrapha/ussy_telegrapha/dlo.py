"""Dead Letter Office — DLQ as Analytical Instrument.

Treats dead letter queues as analytical instruments rather than
graveyards, classifying failures, computing health metrics, and
providing re-routing suggestions.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import DLQEntry, DLOResult

# Signal Corps classification of failure types
FAILURE_TAXONOMY = {
    "address_undecipherable": "Address undecipherable",
    "destination_closed": "Destination closed",
    "no_response": "No response (timeout)",
    "content_indecipherable": "Content indecipherable",
    "regulatory_rejection": "Regulatory rejection",
}

FAILURE_TAXONOMY_DISPLAY = {
    "address_undecipherable": "Address undecipherable",
    "destination_closed": "Destination closed",
    "no_response": "No response (timeout)",
    "content_indecipherable": "Content indecipherable",
    "regulatory_rejection": "Regulatory rejection",
    "unknown": "Unknown",
}


def compute_churn_rate(accumulation_rate: float, resolution_rate: float) -> float:
    """Compute DLQ churn rate.

    Churn = accumulation_rate / resolution_rate
    - churn < 1.0: backlog is shrinking (healthy)
    - churn = 1.0: steady state
    - churn > 1.0: backlog is growing (unhealthy)
    """
    if resolution_rate <= 0:
        return float("inf")
    return accumulation_rate / resolution_rate


def compute_health_score(
    churn_rate: float,
    resolution_rate: float,
    accumulation_rate: float,
    avg_age_hours: float = 0.0,
) -> tuple[float, str]:
    """Compute DLQ health score.

    Health = f(churn, resolution, aging)
    Score is 0.0 (critical) to 1.0 (healthy).

    Args:
        churn_rate: DLQ churn rate.
        resolution_rate: Messages resolved per hour.
        accumulation_rate: Messages arriving per hour.
        avg_age_hours: Average age of DLQ entries.

    Returns:
        Tuple of (health_score, health_status)
    """
    if accumulation_rate <= 0:
        return (1.0, "HEALTHY")

    # Resolution factor: how well we're keeping up
    if churn_rate <= 1.0:
        resolution_factor = 1.0
    else:
        # Penalize for growing backlog
        resolution_factor = 1.0 / churn_rate

    # Resolution efficiency: resolution_rate relative to accumulation
    if accumulation_rate > 0:
        efficiency = min(1.0, resolution_rate / accumulation_rate)
    else:
        efficiency = 1.0

    # Aging factor: older entries are worse
    if avg_age_hours > 0:
        aging_factor = max(0.0, 1.0 - (avg_age_hours / (avg_age_hours + 24.0)))
    else:
        aging_factor = 1.0

    # Combined health score
    health = resolution_factor * efficiency * aging_factor

    # Classify
    if health >= 0.7:
        status = "HEALTHY"
    elif health >= 0.4:
        status = "WARNING"
    else:
        status = "CRITICAL"

    return (round(health, 4), status)


def classify_failure_taxonomy(entries: list[DLQEntry]) -> dict[str, float]:
    """Classify DLQ entries by failure type (Signal Corps classification).

    Returns dict mapping failure_type -> percentage (0.0–1.0).
    """
    if not entries:
        return {}

    counter: Counter[str] = Counter()
    for entry in entries:
        ftype = entry.failure_type if entry.failure_type else "unknown"
        counter[ftype] += 1

    total = len(entries)
    return {k: v / total for k, v in counter.items()}


def find_systemic_source(entries: list[DLQEntry]) -> tuple[str, float]:
    """Find the hop that generates the most DLQ entries.

    Returns:
        Tuple of (source_hop_name, percentage_of_total)
    """
    if not entries:
        return ("", 0.0)

    counter: Counter[str] = Counter()
    for entry in entries:
        if entry.source_hop:
            counter[entry.source_hop] += 1

    if not counter:
        return ("", 0.0)

    most_common = counter.most_common(1)[0]
    percentage = most_common[1] / len(entries)
    return (most_common[0], percentage)


def load_dlq_entries(path: str | Path) -> list[DLQEntry]:
    """Load DLQ entries from a JSON file.

    Expected format:
    {
        "entries": [
            {
                "id": "msg-001",
                "timestamp": "2024-01-15T10:30:00Z",
                "failure_type": "no_response",
                "source_hop": "fraud-service",
                "original_topic": "orders",
                "payload_summary": "Order #12345",
                "age_hours": 2.5
            },
            ...
        ]
    }
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DLQ file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    entries_data = data if isinstance(data, list) else data.get("entries", [])

    entries = []
    for item in entries_data:
        if isinstance(item, dict):
            entries.append(DLQEntry(
                id=item.get("id", ""),
                timestamp=item.get("timestamp", ""),
                failure_type=item.get("failure_type", "unknown"),
                source_hop=item.get("source_hop", ""),
                original_topic=item.get("original_topic", ""),
                payload_summary=item.get("payload_summary", ""),
                age_hours=float(item.get("age_hours", 0.0)),
            ))

    return entries


def analyze_dlo(
    entries: list[DLQEntry],
    accumulation_rate: float | None = None,
    resolution_rate: float | None = None,
) -> DLOResult:
    """Perform full Dead Letter Office analysis.

    Args:
        entries: List of DLQ entries to analyze.
        accumulation_rate: Messages arriving per hour (if not provided, estimated from entries).
        resolution_rate: Messages resolved per hour (if not provided, defaults to 0).

    Returns:
        DLOResult with health metrics, failure taxonomy, and recommendations.
    """
    total = len(entries)

    if accumulation_rate is None:
        # Estimate from entries (rough: assume entries span last hour)
        accumulation_rate = float(total)

    if resolution_rate is None:
        resolution_rate = 0.0

    churn = compute_churn_rate(accumulation_rate, resolution_rate)

    # Failure taxonomy
    taxonomy = classify_failure_taxonomy(entries)

    # Systemic source
    systemic_source, systemic_pct = find_systemic_source(entries)

    # Average age
    avg_age = 0.0
    if entries:
        avg_age = sum(e.age_hours for e in entries) / len(entries)

    # Health score
    health, status = compute_health_score(
        churn, resolution_rate, accumulation_rate, avg_age
    )

    # Recommendations
    recommendations: list[str] = []

    if churn > 1.0:
        recommendations.append(
            f"DLQ backlog is GROWING (churn={churn:.2f}) — "
            f"increase resolution capacity or reduce error rate"
        )

    if systemic_source:
        recommendations.append(
            f"Systemic failure source: {systemic_source} → "
            f"{systemic_pct:.0%} of DLQ entries"
        )
        if systemic_pct > 0.5:
            recommendations.append(
                f"→ Circuit breaker recommended at {systemic_source}"
            )

    # Re-route suggestions based on failure taxonomy
    dest_closed_pct = taxonomy.get("destination_closed", 0.0)
    if dest_closed_pct > 0.2:
        reroute_pct = dest_closed_pct
        recommendations.append(
            f"→ {reroute_pct:.0%} addressable via alternate consumer path "
            f"(destination_closed → re-route)"
        )

    address_undec_pct = taxonomy.get("address_undecipherable", 0.0)
    if address_undec_pct > 0.1:
        recommendations.append(
            f"→ {address_undec_pct:.0%} have missing routing keys — "
            f"add default routing in consumer config"
        )

    content_indec_pct = taxonomy.get("content_indecipherable", 0.0)
    if content_indec_pct > 0.1:
        recommendations.append(
            f"→ {content_indec_pct:.0%} deserialization failures — "
            f"schema migration needed"
        )

    return DLOResult(
        total_entries=total,
        accumulation_rate=accumulation_rate,
        resolution_rate=resolution_rate,
        churn_rate=churn,
        failure_taxonomy=taxonomy,
        health_score=health,
        health_status=status,
        systemic_source=systemic_source,
        systemic_source_pct=systemic_pct,
        recommendations=recommendations,
    )


def format_dlo_report(result: DLOResult) -> str:
    """Format DLO result as a human-readable report."""
    lines: list[str] = []

    lines.append("Dead Letter Office Analysis:")
    lines.append("")
    lines.append(
        f"  Accumulation rate: {result.accumulation_rate:.0f} messages/hour"
    )
    lines.append(
        f"  Resolution rate: {result.resolution_rate:.0f} messages/hour"
    )

    churn_label = "HEALTHY" if result.churn_rate <= 1.0 else "UNHEALTHY — growing backlog"
    lines.append(
        f"  Churn rate: {result.churn_rate:.2f} ({churn_label})"
    )

    lines.append("")
    lines.append("  Failure taxonomy (Signal Corps classification):")
    for ftype, pct in sorted(result.failure_taxonomy.items(), key=lambda x: -x[1]):
        label = FAILURE_TAXONOMY_DISPLAY.get(ftype, ftype)
        lines.append(f"    {label}: {pct:.0%}")

    lines.append("")
    lines.append(
        f"  DLQ Health Score: {result.health_score:.2f} ({result.health_status})"
    )

    if result.systemic_source:
        lines.append(
            f"  Systemic failure source: {result.systemic_source} → "
            f"{result.systemic_source_pct:.0%} of DLQ entries"
        )

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def dlo_to_dict(result: DLOResult) -> dict[str, Any]:
    """Convert DLO result to a JSON-serializable dictionary."""
    return {
        "total_entries": result.total_entries,
        "accumulation_rate": result.accumulation_rate,
        "resolution_rate": result.resolution_rate,
        "churn_rate": round(result.churn_rate, 4),
        "failure_taxonomy": {
            k: round(v, 4) for k, v in result.failure_taxonomy.items()
        },
        "health_score": result.health_score,
        "health_status": result.health_status,
        "systemic_source": result.systemic_source,
        "systemic_source_pct": round(result.systemic_source_pct, 4),
        "recommendations": result.recommendations,
    }
