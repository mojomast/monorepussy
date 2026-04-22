"""Survey — discover pipeline topology from config files.

Supports loading pipeline topology from JSON configuration files
that describe Kafka, RabbitMQ, AWS SQS/SNS, GCP Pub/Sub, or generic stages.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ussy_cyclone.models import PipelineStage, PipelineTopology, topology_from_dict


# Known file patterns for auto-discovery
CONFIG_PATTERNS = [
    "pipeline.json",
    "cyclone.json",
    "topology.json",
    "pipeline_config.json",
]


def discover_config(directory: str) -> Optional[str]:
    """Search a directory for a known pipeline config file.

    Returns the path to the first matching file, or None.
    """
    if not os.path.isdir(directory):
        return None
    for pattern in CONFIG_PATTERNS:
        path = os.path.join(directory, pattern)
        if os.path.isfile(path):
            return path
    # Also check for any .json file containing "pipeline" or "topology"
    for fname in os.listdir(directory):
        if fname.endswith(".json") and ("pipeline" in fname or "topology" in fname):
            return os.path.join(directory, fname)
    return None


def load_topology(source: str) -> PipelineTopology:
    """Load pipeline topology from a file or directory.

    If source is a directory, auto-discovers the config file.
    If source is a file, loads it directly.
    """
    if os.path.isdir(source):
        config_path = discover_config(source)
        if config_path is None:
            raise FileNotFoundError(
                f"No pipeline configuration found in {source}. "
                f"Expected one of: {', '.join(CONFIG_PATTERNS)}"
            )
        source = config_path

    if not os.path.isfile(source):
        raise FileNotFoundError(f"Configuration file not found: {source}")

    with open(source, "r") as f:
        data = json.load(f)

    return topology_from_dict(data)


def survey(source: str) -> Dict[str, Any]:
    """Run a survey of the pipeline, returning topology and summary info.

    Args:
        source: Path to config file or directory.

    Returns:
        Dictionary with topology, stage count, edge count, and summary.
    """
    topology = load_topology(source)

    summary = {
        "topology": topology,
        "stage_count": len(topology.stages),
        "edge_count": len(topology.edges),
        "retry_edge_count": len(topology.retry_edges),
        "stages": [],
    }

    for name, stage in topology.stages.items():
        summary["stages"].append({
            "name": name,
            "type": stage.stage_type,
            "forward_rate": stage.forward_rate,
            "reprocessing_rate": stage.reprocessing_rate,
            "queue_depth": stage.queue_depth,
            "consumer_count": stage.consumer_count,
            "total_throughput": stage.total_throughput,
        })

    return summary


def format_survey(result: Dict[str, Any]) -> str:
    """Format survey results as a human-readable string."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  CYCLONE — Pipeline Survey")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Stages: {result['stage_count']}")
    lines.append(f"  Data flow edges: {result['edge_count']}")
    lines.append(f"  Retry/error edges: {result['retry_edge_count']}")
    lines.append("")

    if result["stages"]:
        lines.append("  Stage Details:")
        lines.append("-" * 60)
        for s in result["stages"]:
            lines.append(
                f"  {s['name']} ({s['type']})  "
                f"fwd={s['forward_rate']:.1f}/s  "
                f"retry={s['reprocessing_rate']:.1f}/s  "
                f"queue={s['queue_depth']}  "
                f"consumers={s['consumer_count']}"
            )

    topology = result["topology"]
    if topology.edges:
        lines.append("")
        lines.append("  Data Flow:")
        for src, dst in topology.edges:
            lines.append(f"    {src} → {dst}")

    if topology.retry_edges:
        lines.append("")
        lines.append("  Retry/Error Flow:")
        for src, dst, gain in topology.retry_edges:
            lines.append(f"    {src} → {dst}  (gain={gain:.2f}x)")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
