"""Report generation — rich terminal output for forensic investigation."""

from __future__ import annotations

from coroner.models import Investigation
from coroner.traces import format_traces
from coroner.spatter import format_spatter
from coroner.striation import format_striation
from coroner.luminol import format_luminol
from coroner.custody import format_custody


def generate_report(investigation: Investigation) -> str:
    """Generate a full autopsy report for a pipeline run.

    Args:
        investigation: The completed investigation.

    Returns:
        Formatted report string.
    """
    lines: list[str] = []

    # Header
    lines.append("=" * 70)
    lines.append(f"CORONER AUTOPSY REPORT — Build #{investigation.run_id}")
    lines.append(f"Investigation timestamp: {investigation.timestamp.isoformat()}")
    lines.append(f"Overall confidence: {investigation.confidence}")
    lines.append("=" * 70)
    lines.append("")

    # Executive Summary
    lines.append("━━━ EXECUTIVE SUMMARY ━━━")
    lines.append(investigation.summary)
    lines.append("")

    # 1. Trace Evidence
    lines.append("━━━ TRACE EVIDENCE (Locard's Exchange Principle) ━━━")
    lines.append(format_traces(investigation.trace_result))
    lines.append("")

    # 2. Error Spatter
    lines.append("━━━ ERROR SPATTER RECONSTRUCTION ━━━")
    lines.append(format_spatter(investigation.spatter_result))
    lines.append("")

    # 3. Striation Matching
    if investigation.striation_matches:
        lines.append("━━━ STRIATION MATCHING (Ballistic Analysis) ━━━")
        lines.append(format_striation(investigation.striation_matches))
        lines.append("")

    # 4. Luminol Scan
    lines.append("━━━ LUMINOL SCAN (Hidden State Detection) ━━━")
    lines.append(format_luminol(investigation.luminol_report))
    lines.append("")

    # 5. Chain of Custody
    lines.append("━━━ CHAIN OF CUSTODY (Artifact Provenance) ━━━")
    lines.append(format_custody(investigation.custody_chain, investigation.custody_comparison))
    lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("END OF AUTOPSY REPORT")
    lines.append("=" * 70)

    return "\n".join(lines)
