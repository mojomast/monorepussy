"""Trace Evidence Collection — Locard's Exchange Principle.

Every pipeline stage interaction leaves bidirectional traces.
Builds a trace transfer matrix with persistence-weighted suspicion scoring.

S(t, i, j) = T[i][j] * P0(t) * e^(-lambda_t * |stage_index(j) - stage_index(i)|)
"""

from __future__ import annotations

import hashlib
from typing import Any

from coroner.models import (
    PipelineRun,
    Stage,
    StageStatus,
    TraceEvidence,
    TraceTransferResult,
    TraceType,
    TRACE_PERSISTENCE,
)


# Transfer probability heuristics between stage types
_TRANSFER_MATRIX: dict[str, dict[str, float]] = {
    "checkout":  {"build": 0.9, "test": 0.3, "deploy": 0.1},
    "build":     {"checkout": 0.2, "test": 0.8, "deploy": 0.4},
    "test":      {"checkout": 0.1, "build": 0.3, "deploy": 0.6},
    "deploy":    {"checkout": 0.05, "build": 0.1, "test": 0.2},
    "lint":      {"build": 0.5, "test": 0.2, "deploy": 0.05},
    "install":   {"build": 0.7, "test": 0.4, "deploy": 0.1},
    "package":   {"deploy": 0.8, "test": 0.3},
}

# Suspicion threshold for flagging reverse traces
SUSPICION_THRESHOLD = 0.7


def _get_transfer_prob(source: str, target: str) -> float:
    """Get transfer probability between two stages."""
    src_key = source.lower()
    tgt_key = target.lower()
    if src_key in _TRANSFER_MATRIX and tgt_key in _TRANSFER_MATRIX[src_key]:
        return _TRANSFER_MATRIX[src_key][tgt_key]
    # Default: inversely proportional to distance
    return 0.3


def _detect_fibers(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect dependency residue (transitive versions) between stages."""
    traces: list[TraceEvidence] = []
    src_deps = {k: v for k, v in source.env_vars.items() if "VERSION" in k or "DEP" in k}
    tgt_deps = {k: v for k, v in target.env_vars.items() if "VERSION" in k or "DEP" in k}
    shared = set(src_deps.keys()) & set(tgt_deps.keys())
    for dep in shared:
        if src_deps[dep] != tgt_deps[dep]:
            traces.append(TraceEvidence(
                source_stage=source.name,
                target_stage=target.name,
                trace_type=TraceType.FIBERS,
                strength=0.8,
                description=f"Dependency version divergence: {dep}={src_deps[dep]} vs {tgt_deps[dep]}",
                source_index=source.index,
                target_index=target.index,
            ))
    return traces


def _detect_dna(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect configuration fingerprints (env+feature flags) between stages."""
    traces: list[TraceEvidence] = []
    src_env = set(source.env_vars.keys())
    tgt_env = set(target.env_vars.keys())
    shared = src_env & tgt_env
    for var in shared:
        if source.env_vars[var] != target.env_vars[var]:
            traces.append(TraceEvidence(
                source_stage=source.name,
                target_stage=target.name,
                trace_type=TraceType.DNA,
                strength=0.7,
                description=f"Configuration divergence: {var}={source.env_vars[var]} vs {target.env_vars[var]}",
                source_index=source.index,
                target_index=target.index,
            ))
    return traces


def _detect_fingerprints(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect build hash digests at stage boundaries."""
    traces: list[TraceEvidence] = []
    shared_artifacts = set(source.artifact_hashes.keys()) & set(target.artifact_hashes.keys())
    for art in shared_artifacts:
        if source.artifact_hashes[art] != target.artifact_hashes[art]:
            traces.append(TraceEvidence(
                source_stage=source.name,
                target_stage=target.name,
                trace_type=TraceType.FINGERPRINTS,
                strength=0.9,
                description=f"Artifact hash changed: {art}",
                source_index=source.index,
                target_index=target.index,
            ))
    return traces


def _detect_soil(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect platform residue (OS, kernel, arch) between stages."""
    traces: list[TraceEvidence] = []
    platform_vars = {"OS", "PLATFORM", "ARCH", "KERNEL", "RUNNER_OS", "RUNNER_ARCH"}
    for var in platform_vars:
        src_val = source.env_vars.get(var, "")
        tgt_val = target.env_vars.get(var, "")
        if src_val and tgt_val and src_val != tgt_val:
            traces.append(TraceEvidence(
                source_stage=source.name,
                target_stage=target.name,
                trace_type=TraceType.SOIL,
                strength=0.6,
                description=f"Platform divergence: {var}={src_val} vs {tgt_val}",
                source_index=source.index,
                target_index=target.index,
            ))
    return traces


def _detect_tool_marks(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect toolchain impressions (compiler flags, versions) between stages."""
    traces: list[TraceEvidence] = []
    tool_vars = {"CC", "CXX", "COMPILER", "NODE_VERSION", "PYTHON_VERSION", "GCC_VERSION"}
    for var in tool_vars:
        src_val = source.env_vars.get(var, "")
        tgt_val = target.env_vars.get(var, "")
        if src_val and tgt_val and src_val != tgt_val:
            traces.append(TraceEvidence(
                source_stage=source.name,
                target_stage=target.name,
                trace_type=TraceType.TOOL_MARKS,
                strength=0.8,
                description=f"Toolchain divergence: {var}={src_val} vs {tgt_val}",
                source_index=source.index,
                target_index=target.index,
            ))
    return traces


def _detect_glass_fragments(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect artifact shards (partial outputs, intermediate files)."""
    traces: list[TraceEvidence] = []
    src_arts = set(source.artifact_hashes.keys())
    tgt_arts = set(target.artifact_hashes.keys())
    # Artifacts in target but not source (partial outputs leaked forward)
    new_in_target = tgt_arts - src_arts
    for art in new_in_target:
        traces.append(TraceEvidence(
            source_stage=source.name,
            target_stage=target.name,
            trace_type=TraceType.GLASS_FRAGMENTS,
            strength=0.5,
            description=f"New artifact shard in target: {art}",
            source_index=source.index,
            target_index=target.index,
        ))
    return traces


def _detect_paint_layers(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Detect Docker layer provenance changes."""
    traces: list[TraceEvidence] = []
    for key in source.artifact_hashes:
        if "layer" in key.lower() or "docker" in key.lower():
            if key in target.artifact_hashes and source.artifact_hashes[key] != target.artifact_hashes[key]:
                traces.append(TraceEvidence(
                    source_stage=source.name,
                    target_stage=target.name,
                    trace_type=TraceType.PAINT_LAYERS,
                    strength=0.7,
                    description=f"Docker layer changed: {key}",
                    source_index=source.index,
                    target_index=target.index,
                ))
    return traces


_DETECTORS = [
    _detect_fibers,
    _detect_dna,
    _detect_fingerprints,
    _detect_soil,
    _detect_tool_marks,
    _detect_glass_fragments,
    _detect_paint_layers,
]


def _detect_traces_between(source: Stage, target: Stage) -> list[TraceEvidence]:
    """Run all trace detectors between two stages."""
    all_traces: list[TraceEvidence] = []
    for detector in _DETECTORS:
        all_traces.extend(detector(source, target))
    return all_traces


def _check_missing_traces(stage: Stage) -> list[TraceEvidence]:
    """Check for suspiciously missing traces — stages with no artifact changes."""
    missing: list[TraceEvidence] = []
    if stage.status == StageStatus.SUCCESS and not stage.artifact_hashes:
        # Stage reported success but left no artifact hash change — likely skipped work
        missing.append(TraceEvidence(
            source_stage=stage.name,
            target_stage=stage.name,
            trace_type=TraceType.FINGERPRINTS,
            strength=0.0,
            description=f"Stage {stage.name} reported success but left no artifact hash changes (possibly skipped real work)",
            source_index=stage.index,
            target_index=stage.index,
        ))
    return missing


def analyze_traces(run: PipelineRun, bidirectional: bool = True) -> TraceTransferResult:
    """Analyze trace evidence for a pipeline run using Locard's Exchange Principle.

    Args:
        run: The pipeline run to analyze.
        bidirectional: If True, also check reverse (downstream->upstream) traces.

    Returns:
        TraceTransferResult with forward, reverse, and suspicious traces.
    """
    result = TraceTransferResult()
    stages = run.stages
    if len(stages) < 2:
        return result

    # Forward traces (upstream -> downstream)
    for i in range(len(stages)):
        for j in range(i + 1, len(stages)):
            traces = _detect_traces_between(stages[i], stages[j])
            # Apply transfer probability weighting
            t_prob = _get_transfer_prob(stages[i].name, stages[j].name)
            for t in traces:
                t.strength *= t_prob
                t.suspicion_score = t.strength * pow(
                    2.718281828,
                    -TRACE_PERSISTENCE[t.trace_type] * abs(t.target_index - t.source_index),
                )
            result.forward_traces.extend(traces)

    # Reverse traces (downstream -> upstream) — bidirectional contamination
    if bidirectional:
        for i in range(len(stages)):
            for j in range(i):
                traces = _detect_traces_between(stages[i], stages[j])
                t_prob = _get_transfer_prob(stages[i].name, stages[j].name)
                for t in traces:
                    t.strength *= t_prob * 1.5  # Reverse traces are more suspicious
                    t.suspicion_score = t.strength * pow(
                        2.718281828,
                        -TRACE_PERSISTENCE[t.trace_type] * abs(t.target_index - t.source_index),
                    )
                result.reverse_traces.extend(traces)

    # Check for suspiciously missing traces
    for stage in stages:
        result.forward_traces.extend(_check_missing_traces(stage))

    # Identify suspicious transfers
    all_traces = result.forward_traces + result.reverse_traces
    result.suspicious_transfers = [
        t for t in all_traces
        if t.suspicion_score > SUSPICION_THRESHOLD
    ]
    # Sort by suspicion score descending
    result.suspicious_transfers.sort(key=lambda t: t.suspicion_score, reverse=True)

    return result


def format_traces(result: TraceTransferResult, bidirectional: bool = True) -> str:
    """Format trace analysis results for display."""
    lines: list[str] = []

    # Forward traces
    if result.forward_traces:
        # Group by source->target pair
        pairs: dict[str, list[TraceEvidence]] = {}
        for t in result.forward_traces:
            key = f"{t.source_stage}→{t.target_stage}"
            pairs.setdefault(key, []).append(t)
        for pair, traces in pairs.items():
            type_counts: dict[str, int] = {}
            for t in traces:
                type_counts[t.trace_type.value] = type_counts.get(t.trace_type.value, 0) + 1
            count_str = ", ".join(f"{c} {v}" for v, c in type_counts.items())
            lines.append(f"Stage {pair}: {len(traces)} traces transferred ({count_str})")

    # Reverse traces
    if bidirectional and result.reverse_traces:
        lines.append("")
        for t in result.reverse_traces:
            if t.suspicion_score > 0.5:
                lines.append(
                    f"⚠️  Suspicious: Stage {t.source_stage} left traces on {t.target_stage} "
                    f"(bidirectional contamination)"
                )
                lines.append(f"    {t.description}")
                level = "HIGH" if t.suspicion_score > 0.8 else "MEDIUM"
                lines.append(f"    Suspicion score: {t.suspicion_score:.2f} ({level})")

    # Suspicious transfers summary
    if result.suspicious_transfers:
        lines.append("")
        lines.append("=== Most Suspicious Traces ===")
        for t in result.suspicious_transfers[:5]:
            direction = "→" if t.source_index < t.target_index else "←"
            lines.append(
                f"  {t.source_stage} {direction} {t.target_stage}: "
                f"{t.trace_type.value} (score={t.suspicion_score:.2f})"
            )
            lines.append(f"    {t.description}")

    return "\n".join(lines)
