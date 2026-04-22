"""Capability Index — Process Capability Cp/Cpk.

Cp  = (USL - LSL) / (6 * sigma_within)
Cpk = min((USL - mean) / (3 * sigma_within), (mean - LSL) / (3 * sigma_within))
Pp  = (USL - LSL) / (6 * sigma_overall)
Ppk = min((USL - mean) / (3 * sigma_overall), (mean - LSL) / (3 * sigma_overall))

Cpk < 1.0  → more than 0.27% of results outside specification
Cpk < 1.33 → not a capable measurement instrument (industry standard)
Cpk >= 1.33 → capable
Cpk >= 2.0  → excellent (Six Sigma)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_calibre.models import CapabilityResult, CapabilitySpec, TestRun


def compute_cp(usl: float, lsl: float, sigma_within: float) -> float:
    """Compute Cp (potential capability)."""
    if sigma_within <= 0:
        return float("inf") if usl > lsl else 0.0
    return (usl - lsl) / (6.0 * sigma_within)


def compute_cpk(usl: float, lsl: float, mean: float, sigma_within: float) -> float:
    """Compute Cpk (actual capability accounting for off-centering)."""
    if sigma_within <= 0:
        return float("inf")
    cpu = (usl - mean) / (3.0 * sigma_within)
    cpl = (mean - lsl) / (3.0 * sigma_within)
    return min(cpu, cpl)


def compute_pp(usl: float, lsl: float, sigma_overall: float) -> float:
    """Compute Pp (potential performance)."""
    if sigma_overall <= 0:
        return float("inf") if usl > lsl else 0.0
    return (usl - lsl) / (6.0 * sigma_overall)


def compute_ppk(usl: float, lsl: float, mean: float, sigma_overall: float) -> float:
    """Compute Ppk (actual performance)."""
    if sigma_overall <= 0:
        return float("inf")
    ppu = (usl - mean) / (3.0 * sigma_overall)
    ppl = (mean - lsl) / (3.0 * sigma_overall)
    return min(ppu, ppl)


def estimate_sigma_within(runs: List[TestRun]) -> float:
    """Estimate within-subgroup (short-term) sigma from test runs.

    Groups runs by build_id as subgroups and computes pooled within-group std.
    """
    if not runs:
        return 0.0

    by_build: Dict[str, List[float]] = {}
    for r in runs:
        by_build.setdefault(r.build_id, []).append(r.numeric_result)

    # Pooled within-group variance
    total_var = 0.0
    total_df = 0
    for values in by_build.values():
        if len(values) >= 2:
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            total_var += var * (len(values) - 1)
            total_df += len(values) - 1

    if total_df > 0:
        return (total_var / total_df) ** 0.5
    return 0.0


def estimate_sigma_overall(runs: List[TestRun]) -> float:
    """Estimate overall (long-term) sigma from all test runs."""
    if len(runs) < 2:
        return 0.0
    values = [r.numeric_result for r in runs]
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return var ** 0.5


def capability_analysis(
    runs: List[TestRun],
    spec: CapabilitySpec,
) -> CapabilityResult:
    """Perform capability analysis for a test against specification limits."""
    if not runs:
        return CapabilityResult(
            test_name=spec.test_name,
            usl=spec.usl,
            lsl=spec.lsl,
            diagnosis="No data available",
        )

    values = [r.numeric_result for r in runs]
    mean = sum(values) / len(values)

    sigma_within = estimate_sigma_within(runs)
    sigma_overall = estimate_sigma_overall(runs)

    cp = compute_cp(spec.usl, spec.lsl, sigma_within)
    cpk = compute_cpk(spec.usl, spec.lsl, mean, sigma_within)
    pp = compute_pp(spec.usl, spec.lsl, sigma_overall)
    ppk = compute_ppk(spec.usl, spec.lsl, mean, sigma_overall)

    # Determine if capable (industry standard Cpk >= 1.33)
    capable = cpk >= 1.33 if cpk != float("inf") else False

    # Diagnosis
    if cpk == float("inf"):
        diagnosis = "Zero variation — suite always produces same result (may not be measuring anything)"
    elif cpk < 1.0:
        diagnosis = "Cpk < 1.0 — suite is NOT a capable measurement instrument (>0.27% outside spec)"
    elif cpk < 1.33:
        diagnosis = "Cpk < 1.33 — suite does not meet industry capability standard"
    else:
        diagnosis = "Cpk >= 1.33 — suite is a capable measurement instrument"

    if cp != float("inf") and cpk != float("inf"):
        gap = cp - cpk
        if gap > 0.5:
            diagnosis += " | Large Cp-Cpk gap: suite is significantly off-center"

    return CapabilityResult(
        test_name=spec.test_name,
        cp=cp,
        cpk=cpk,
        pp=pp,
        ppk=ppk,
        mean=mean,
        sigma_within=sigma_within,
        sigma_overall=sigma_overall,
        usl=spec.usl,
        lsl=spec.lsl,
        capable=capable,
        diagnosis=diagnosis,
    )


def format_capability(result: CapabilityResult) -> str:
    """Format capability analysis results."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Capability Analysis: {result.test_name}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append(f"  Specification: LSL={result.lsl:.4f}  USL={result.usl:.4f}")
    lines.append(f"  Mean: {result.mean:.4f}")
    lines.append(f"  Sigma (within):  {result.sigma_within:.4f}")
    lines.append(f"  Sigma (overall): {result.sigma_overall:.4f}")
    lines.append("")

    def _fmt(val: float) -> str:
        return f"{val:.4f}" if val != float("inf") else "∞"

    lines.append(f"  Cp  = {_fmt(result.cp)}    (potential capability)")
    lines.append(f"  Cpk = {_fmt(result.cpk)}   (actual capability)")
    lines.append(f"  Pp  = {_fmt(result.pp)}    (potential performance)")
    lines.append(f"  Ppk = {_fmt(result.ppk)}   (actual performance)")
    lines.append("")
    lines.append(f"  Capable: {'YES' if result.capable else 'NO'}")
    lines.append(f"  Diagnosis: {result.diagnosis}")
    lines.append("")

    return "\n".join(lines)
