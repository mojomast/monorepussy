"""Luminol Scan — Hidden State Detection.

Two-phase presumptive + confirmatory testing for invisible state corruption:
- Cache luminol: Verify cache integrity (hash comparison against known-good state)
- Ninhydrin scan: Detect undeclared state mutations
- Confirmatory re-run: Eliminate false positives
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from coroner.models import (
    LuminolFinding,
    LuminolReport,
    LuminolResult,
    PipelineRun,
    Stage,
    StageStatus,
)


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of string content."""
    return hashlib.sha256(content.encode()).hexdigest()


def cache_luminol(run: PipelineRun) -> list[LuminolFinding]:
    """Phase 1a: Cache luminol — verify cache integrity.

    Checks for hash mismatches in artifacts that should have stable content.
    """
    findings: list[LuminolFinding] = []

    for i, stage in enumerate(run.stages):
        # Check artifact hashes for stages that succeeded
        # (succeeded stages should have deterministic outputs)
        if stage.status == StageStatus.SUCCESS:
            # Look for cache-like artifacts
            for art_name, art_hash in stage.artifact_hashes.items():
                # Check if this artifact was modified by a later stage
                for j in range(i + 1, len(run.stages)):
                    later = run.stages[j]
                    if art_name in later.artifact_hashes:
                        if later.artifact_hashes[art_name] != art_hash:
                            finding = LuminolFinding(
                                category="cache",
                                path=art_name,
                                expected_hash=art_hash,
                                actual_hash=later.artifact_hashes[art_name],
                                source_stage=stage.name,
                                target_stage=later.name,
                                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                                description=(
                                    f"Cache artifact {art_name} modified by later stage: "
                                    f"expected {art_hash[:8]}... got {later.artifact_hashes[art_name][:8]}..."
                                ),
                            )
                            findings.append(finding)

        # Check for empty hashes on expected artifacts
        if stage.status == StageStatus.SUCCESS and not stage.artifact_hashes:
            # Stage succeeded but no artifact hashes — suspicious
            finding = LuminolFinding(
                category="cache",
                path=f"stage_{stage.name}",
                source_stage=stage.name,
                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                description=(
                    f"Stage {stage.name} reported success but produced no verifiable artifact hashes"
                ),
            )
            findings.append(finding)

    return findings


def ninhydrin_scan(run: PipelineRun) -> list[LuminolFinding]:
    """Phase 1b: Ninhydrin scan — detect undeclared state mutations.

    Finds environment variables that change between stages without being
    explicitly declared as dependencies.
    """
    findings: list[LuminolFinding] = []

    for i in range(len(run.stages) - 1):
        current = run.stages[i]
        next_stage = run.stages[i + 1]

        # Find env vars present in next stage but not in current
        current_vars = set(current.env_vars.keys())
        next_vars = set(next_stage.env_vars.keys())

        # New variables introduced
        new_vars = next_vars - current_vars
        # Changed variables
        changed_vars = [
            v for v in current_vars & next_vars
            if current.env_vars[v] != next_stage.env_vars[v]
        ]

        undeclared = sorted(new_vars | set(changed_vars))

        # Filter out well-known CI variables
        well_known = {
            "PATH", "HOME", "USER", "SHELL", "PWD", "LANG", "TERM",
            "CI", "CI_JOB_ID", "CI_PIPELINE_ID", "CI_BUILD_ID",
            "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER",
        }
        undeclared = [v for v in undeclared if v not in well_known]

        if undeclared:
            finding = LuminolFinding(
                category="ninhydrin",
                source_stage=current.name,
                target_stage=next_stage.name,
                env_vars=undeclared,
                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                description=(
                    f"Stage {current.name} → Stage {next_stage.name}: "
                    f"{len(undeclared)} undeclared env vars ({', '.join(undeclared[:5])})"
                ),
            )
            findings.append(finding)

    return findings


def confirmatory_test(
    run: PipelineRun,
    presumptive_findings: list[LuminolFinding],
) -> list[LuminolFinding]:
    """Phase 2: Confirmatory testing — eliminate false positives.

    Simulates re-running with controlled state by checking if the
    same conditions persist across multiple indicators.
    """
    confirmed: list[LuminolFinding] = []

    # A finding is confirmed if multiple independent indicators agree
    cache_findings = [f for f in presumptive_findings if f.category == "cache"]
    ninhydrin_findings = [f for f in presumptive_findings if f.category == "ninhydrin"]

    # Cache findings with hash mismatches are confirmed if there's also
    # a ninhydrin finding for the same stage pair
    for cf in cache_findings:
        if cf.result != LuminolResult.PRESUMPTIVE_POSITIVE:
            continue
        # Check for corroborating ninhydrin evidence
        corroborated = any(
            nf.source_stage == cf.source_stage or nf.target_stage == cf.target_stage
            for nf in ninhydrin_findings
        )
        if corroborated or len(cache_findings) >= 2:
            confirmed.append(LuminolFinding(
                category="confirmatory",
                path=cf.path,
                expected_hash=cf.expected_hash,
                actual_hash=cf.actual_hash,
                source_stage=cf.source_stage,
                target_stage=cf.target_stage,
                result=LuminolResult.CONFIRMED,
                description=f"CONFIRMED: {cf.description}",
            ))
        else:
            # Single indicator — remains presumptive but not confirmed
            confirmed.append(cf)

    # Ninhydrin findings with multiple undeclared vars are more likely real
    for nf in ninhydrin_findings:
        if len(nf.env_vars) >= 3:
            confirmed.append(LuminolFinding(
                category="confirmatory",
                source_stage=nf.source_stage,
                target_stage=nf.target_stage,
                env_vars=nf.env_vars,
                result=LuminolResult.CONFIRMED,
                description=f"CONFIRMED: {nf.description}",
            ))
        else:
            confirmed.append(nf)

    return confirmed


def analyze_luminol(run: PipelineRun) -> LuminolReport:
    """Perform complete luminol scan on a pipeline run.

    Two-phase presumptive + confirmatory testing for hidden state corruption.

    Args:
        run: The pipeline run to scan.

    Returns:
        LuminolReport with findings and root cause assessment.
    """
    # Phase 1: Presumptive testing
    cache_findings = cache_luminol(run)
    ninhydrin_findings = ninhydrin_scan(run)
    presumptive = cache_findings + ninhydrin_findings

    # Phase 2: Confirmatory testing
    confirmed = confirmatory_test(run, presumptive)

    # Build root cause description
    confirmed_findings = [f for f in confirmed if f.result == LuminolResult.CONFIRMED]
    presumptive_only = [f for f in confirmed if f.result == LuminolResult.PRESUMPTIVE_POSITIVE]

    root_cause = ""
    is_confirmed = False

    if confirmed_findings:
        is_confirmed = True
        parts: list[str] = []
        for f in confirmed_findings:
            if f.category == "cache":
                parts.append(f"Cache corruption detected: {f.description}")
            elif f.category == "ninhydrin":
                parts.append(f"Hidden state dependency: {f.description}")
        root_cause = "; ".join(parts) if parts else "Hidden state corruption confirmed"
    elif presumptive_only:
        root_cause = "Presumptive positive: possible hidden state corruption (not confirmed)"
    else:
        root_cause = "No hidden state corruption detected"

    return LuminolReport(
        findings=confirmed,
        root_cause=root_cause,
        confirmed=is_confirmed,
    )


def format_luminol(report: LuminolReport) -> str:
    """Format luminol scan results for display."""
    lines: list[str] = []

    # Cache luminol findings
    cache_findings = [f for f in report.findings if f.category in ("cache", "confirmatory") and f.path]
    if cache_findings:
        lines.append("🔍 Cache Luminol:")
        for f in cache_findings:
            if f.expected_hash and f.actual_hash:
                lines.append(
                    f"  {f.path}: HASH MISMATCH "
                    f"(expected {f.expected_hash[:8]}... got {f.actual_hash[:8]}...)"
                )
            else:
                lines.append(f"  {f.path}: {f.description}")
            if f.result == LuminolResult.PRESUMPTIVE_POSITIVE:
                lines.append("  ⚠️  Presumptive positive: stale dependency cache")
            elif f.result == LuminolResult.CONFIRMED:
                lines.append("  ✅ Confirmed: cache integrity violation")

    # Ninhydrin findings
    ninhydrin_findings = [f for f in report.findings if f.category in ("ninhydrin", "confirmatory") and f.env_vars]
    if ninhydrin_findings:
        lines.append("")
        lines.append("🧪 Ninhydrin Scan:")
        for f in ninhydrin_findings:
            var_list = ", ".join(f.env_vars[:5])
            lines.append(
                f"  Stage {f.source_stage} → Stage {f.target_stage}: "
                f"{len(f.env_vars)} undeclared env vars ({var_list})"
            )
            if f.result == LuminolResult.PRESUMPTIVE_POSITIVE:
                lines.append("  ⚠️  Presumptive positive: hidden state dependency")
            elif f.result == LuminolResult.CONFIRMED:
                lines.append("  ✅ Confirmed: undeclared state mutation")

    # Confirmatory
    confirmed = [f for f in report.findings if f.result == LuminolResult.CONFIRMED]
    if confirmed:
        lines.append("")
        lines.append("✅ Confirmatory: Hidden state corruption CONFIRMED")
    elif report.findings:
        lines.append("")
        lines.append("⚠️  Presumptive only — not enough evidence to confirm")

    # Root cause
    if report.root_cause:
        lines.append("")
        lines.append(f"Root cause: {report.root_cause}")

    if not report.findings:
        lines.append("No hidden state corruption detected.")

    return "\n".join(lines)
