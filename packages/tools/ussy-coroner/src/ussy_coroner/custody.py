"""Chain of Custody — Artifact Provenance.

Hash-chain provenance tracking for every artifact through pipeline stages.

H_n = H(H_{n-1} || handler_n || t_n || action_n)

Cross-run comparison detects input divergence, process divergence, and nondeterminism.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from ussy_coroner.models import (
    CustodyChain,
    CustodyComparison,
    CustodyEntry,
    PipelineRun,
    Stage,
)


def build_custody_chain(run: PipelineRun) -> CustodyChain:
    """Build a hash-chain custody trail for a pipeline run.

    H_n = H(H_{n-1} || handler_n || t_n || action_n)

    Args:
        run: The pipeline run to build custody chain for.

    Returns:
        CustodyChain with computed hash values.
    """
    chain = CustodyChain(run_id=run.run_id)

    # Genesis hash
    previous_hash = "0" * 64  # SHA-256 zero hash

    for stage in run.stages:
        # Handler is the stage name
        handler = stage.name
        # Action summarizes what the stage did
        action = _summarize_action(stage)
        # Timestamp
        ts = stage.start_time or datetime.now(timezone.utc)

        entry = CustodyEntry(
            stage_name=stage.name,
            stage_index=stage.index,
            handler=handler,
            timestamp=ts,
            action=action,
        )

        previous_hash = entry.compute_hash(previous_hash)
        chain.entries.append(entry)

    return chain


def _summarize_action(stage: Stage) -> str:
    """Summarize a stage's action for the custody chain."""
    parts: list[str] = [f"status={stage.status.value}"]

    if stage.artifact_hashes:
        # Include sorted artifact hashes for determinism
        sorted_hashes = sorted(stage.artifact_hashes.items())
        hash_str = ",".join(f"{k}={v[:8]}" for k, v in sorted_hashes)
        parts.append(f"artifacts=[{hash_str}]")

    if stage.env_vars:
        # Include relevant env vars (sorted for determinism)
        sorted_env = sorted(stage.env_vars.items())
        env_str = ",".join(f"{k}={v}" for k, v in sorted_env[:10])
        parts.append(f"env=[{env_str}]")

    return ";".join(parts)


def compare_custody_chains(
    chain1: CustodyChain,
    chain2: CustodyChain,
) -> CustodyComparison:
    """Compare custody chains between two pipeline runs.

    Detects:
    - Input divergence: different inputs at the same stage
    - Process divergence: different process (toolchain, env) at the same stage
    - Nondeterminism: same inputs + same process but different outputs

    Args:
        chain1: First run's custody chain.
        chain2: Second run's custody chain.

    Returns:
        CustodyComparison with divergence analysis.
    """
    comparison = CustodyComparison(
        run_id_1=chain1.run_id,
        run_id_2=chain2.run_id,
    )

    # Find the first divergence point
    max_stages = min(len(chain1.entries), len(chain2.entries))

    for i in range(max_stages):
        e1 = chain1.entries[i]
        e2 = chain2.entries[i]

        if e1.hash_value != e2.hash_value:
            comparison.divergence_stage = e1.stage_name
            comparison.divergence_index = i

            # Analyze the divergence
            # Parse the action summaries to detect input vs process vs output divergence
            a1 = e1.action
            a2 = e2.action

            # Check if inputs are the same
            # Inputs are determined by the previous stage's hash
            prev_same = True
            if i > 0:
                prev_same = chain1.entries[i - 1].hash_value == chain2.entries[i - 1].hash_value

            comparison.same_inputs = prev_same

            # Check if process is the same (env vars match)
            env1 = _extract_env_from_action(a1)
            env2 = _extract_env_from_action(a2)
            comparison.same_process = env1 == env2

            # Nondeterminism: same inputs + same process but different outputs
            comparison.nondeterminism = comparison.same_inputs and comparison.same_process

            # Generate likely cause
            if comparison.nondeterminism:
                comparison.likely_cause = (
                    f"SAME INPUTS, DIFFERENT OUTPUTS → nondeterminism detected at stage {e1.stage_name}"
                )
            elif not comparison.same_inputs and not comparison.same_process:
                comparison.likely_cause = (
                    f"Both inputs and process diverged at stage {e1.stage_name}"
                )
            elif not comparison.same_inputs:
                comparison.likely_cause = (
                    f"Input divergence at stage {e1.stage_name}"
                )
            else:
                comparison.likely_cause = (
                    f"Process divergence at stage {e1.stage_name} "
                    f"(e.g., toolchain version drift)"
                )

            break

    # If no divergence found
    if not comparison.divergence_stage:
        if len(chain1.entries) != len(chain2.entries):
            comparison.divergence_stage = "pipeline_length"
            comparison.likely_cause = "Different number of stages in the two runs"
        else:
            comparison.same_inputs = True
            comparison.same_process = True
            comparison.likely_cause = "Custody chains match completely"

    return comparison


def _extract_env_from_action(action: str) -> dict[str, str]:
    """Extract environment variables from action summary string."""
    env: dict[str, str] = {}
    if "env=[" not in action:
        return env
    start = action.index("env=[") + 5
    end = action.index("]", start)
    env_str = action[start:end]
    for pair in env_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            env[k] = v
    return env


def analyze_custody(
    run: PipelineRun,
    compare_run: PipelineRun | None = None,
) -> tuple[CustodyChain, CustodyComparison | None]:
    """Analyze chain of custody for a pipeline run.

    Args:
        run: The primary pipeline run.
        compare_run: Optional second run for cross-run comparison.

    Returns:
        Tuple of (CustodyChain, optional CustodyComparison).
    """
    chain = build_custody_chain(run)
    comparison = None

    if compare_run:
        chain2 = build_custody_chain(compare_run)
        comparison = compare_custody_chains(chain, chain2)

    return (chain, comparison)


def format_custody(chain: CustodyChain, comparison: CustodyComparison | None = None) -> str:
    """Format custody chain results for display."""
    lines: list[str] = []

    # Custody chain
    lines.append("=== Chain of Custody ===")
    for entry in chain.entries:
        lines.append(
            f"Stage {entry.stage_name}: H_{entry.stage_index} = {entry.hash_value[:8]}... "
            f"({entry.action[:60]}{'...' if len(entry.action) > 60 else ''})"
        )

    # Comparison
    if comparison:
        lines.append("")
        lines.append(f"=== Comparison: {comparison.run_id_1} vs {comparison.run_id_2} ===")

        if comparison.divergence_stage and comparison.divergence_stage != "pipeline_length":
            lines.append(
                f"Stage {comparison.divergence_stage}: CUSTODY DIVERGED at H_{comparison.divergence_index}"
            )
            if comparison.nondeterminism:
                lines.append("  ⚠️  SAME INPUTS, DIFFERENT OUTPUTS → nondeterminism detected")
            elif not comparison.same_inputs:
                lines.append("  Input divergence detected")
            elif not comparison.same_process:
                lines.append("  Process divergence detected (e.g., toolchain version drift)")
            lines.append(f"  {comparison.likely_cause}")
        elif comparison.divergence_stage == "pipeline_length":
            lines.append("  ⚠️  Different pipeline lengths between runs")
            lines.append(f"  {comparison.likely_cause}")
        else:
            lines.append("  ✅ Custody chains match completely")

    return "\n".join(lines)
