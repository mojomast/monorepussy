"""Report generation for Gridiron analysis."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TextIO

from gridiron.models import (
    ComplianceResult,
    FullReport,
    HealthStatus,
    N1Report,
    FrequencyReport,
    OPFReport,
    RelayReport,
    VoltageReport,
    GridCodeReport,
    SystemState,
)


class ReportFormatter:
    """Format analysis reports for output."""

    def __init__(self, out: TextIO = sys.stdout) -> None:
        self.out = out

    def format_full_report(self, report: FullReport, fmt: str = "text") -> str:
        """Format a full Grid Reliability Assessment."""
        if fmt == "json":
            return self._format_json(report)
        return self._format_text(report)

    def _format_text(self, report: FullReport) -> str:
        """Format report as human-readable text."""
        lines: list = []
        lines.append("=" * 70)
        lines.append("GRIDIRON — Grid Reliability Assessment")
        lines.append("=" * 70)
        lines.append(f"Project: {report.project_path}")
        lines.append(f"Timestamp: {report.timestamp.isoformat()}")
        lines.append(f"Overall Status: {report.overall_status.value.upper()}")
        lines.append("")

        if report.n1_report:
            lines.append(self._format_n1(report.n1_report))
            lines.append("")

        if report.frequency_report:
            lines.append(self._format_frequency(report.frequency_report))
            lines.append("")

        if report.opf_report:
            lines.append(self._format_opf(report.opf_report))
            lines.append("")

        if report.relay_report:
            lines.append(self._format_relay(report.relay_report))
            lines.append("")

        if report.voltage_report:
            lines.append(self._format_voltage(report.voltage_report))
            lines.append("")

        if report.grid_code_reports:
            lines.append(self._format_grid_codes(report.grid_code_reports))
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _format_n1(self, report: N1Report) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("N-1 CONTINGENCY ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Total Packages: {report.total_packages}")
        lines.append(f"Passing N-1: {report.passing_packages}")
        lines.append(f"N-1 Compliance Score: {report.compliance_score:.1f}%")
        lines.append("")

        if report.spof_register:
            lines.append("SPOF Register (ranked by blast radius):")
            for i, spof in enumerate(report.spof_register, 1):
                lines.append(
                    f"  {i}. {spof.removed_package} "
                    f"(blast radius: {spof.blast_radius:.1f}, "
                    f"affected: {len(spof.affected_packages)}, "
                    f"state: {spof.system_state.value})"
                )
                if spof.recommendation:
                    lines.append(f"     → {spof.recommendation}")
        else:
            lines.append("No Single Points of Failure detected.")

        return "\n".join(lines)

    def _format_frequency(self, report: FrequencyReport) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("FREQUENCY MONITOR — Version Shock Response")
        lines.append("-" * 40)
        lines.append(f"Average Frequency Deviation: {report.average_deviation:.4f}")
        lines.append(f"Worst Frequency Deviation: {report.worst_deviation:.4f}")
        lines.append("")

        for result in report.results:
            lines.append(f"  Shock: {result.shock.package} "
                         f"({result.shock.old_version} → {result.shock.new_version})")
            lines.append(f"    Deviation: {result.frequency_deviation:.4f}")
            lines.append(f"    Primary Recovery: {result.primary_recovery:.1%}")
            lines.append(f"    Secondary Recovery: {result.secondary_recovery:.1%}")
            lines.append(f"    Tertiary Needed: {'Yes' if result.tertiary_needed else 'No'}")
            lines.append(f"    AGC Time to 95%: {result.agc_equivalency_time:.1f} hours")
            if result.rigid_transmitters:
                lines.append(f"    Rigid Transmitters: {', '.join(result.rigid_transmitters)}")

        return "\n".join(lines)

    def _format_opf(self, report: OPFReport) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("FLOW OPTIMIZER — Optimal Dependency Dispatch")
        lines.append("-" * 40)
        lines.append(f"Total Risk: {report.total_risk:.3f}")
        lines.append("")

        lines.append("Optimal Dispatch:")
        for d in report.dispatch:
            status = " [CONGESTED]" if d.is_congested else ""
            lines.append(
                f"  {d.package}: weight={d.optimal_weight:.3f}, "
                f"risk={d.risk_contribution:.3f}{status}"
            )

        if report.overcoupled_pairs:
            lines.append("")
            lines.append("Overcoupled Pairs:")
            for src, tgt in report.overcoupled_pairs:
                lines.append(f"  {src} → {tgt}")

        if report.redispatch_recommendations:
            lines.append("")
            lines.append("Redispatch Recommendations:")
            for rec in report.redispatch_recommendations:
                lines.append(f"  → {rec}")

        return "\n".join(lines)

    def _format_relay(self, report: RelayReport) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("RELAY COORDINATOR — Protection Coordination")
        lines.append("-" * 40)
        lines.append(f"Error Handlers Found: {len(report.handlers)}")
        lines.append("")

        if report.cti_violations:
            lines.append("CTI Violations:")
            for v in report.cti_violations:
                lines.append(
                    f"  {v.primary_handler} → {v.backup_handler}: "
                    f"CTI={v.cti_actual:.3f}s (required: {v.cti_required:.3f}s) "
                    f"[{v.violation_severity}]"
                )
        else:
            lines.append("No CTI violations detected.")

        if report.blind_spots:
            lines.append("")
            lines.append(f"Blind Spots (no handler coverage): {', '.join(report.blind_spots)}")

        if report.tcc_overlaps:
            lines.append("")
            lines.append("TCC Overlaps (collision risk):")
            for h1, h2 in report.tcc_overlaps:
                lines.append(f"  {h1} ↔ {h2}")

        return "\n".join(lines)

    def _format_voltage(self, report: VoltageReport) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("VOLTAGE ANALYST — Capability & Collapse Proximity")
        lines.append("-" * 40)
        lines.append("")

        lines.append("Package Health Voltages:")
        for result in report.package_results:
            sag_marker = " ⚠ SAGGING" if result.is_sagging else ""
            lines.append(
                f"  {result.package}: V={result.health_voltage:.3f} pu, "
                f"Q_margin={result.q_margin:.3f}, "
                f"CPI={result.collapse_proximity_index:.3f}{sag_marker}"
            )

        if report.weakest_packages:
            lines.append("")
            lines.append(f"Weakest Packages: {', '.join(report.weakest_packages)}")

        if report.reactive_compensation_recommendations:
            lines.append("")
            lines.append("Reactive Compensation Recommendations:")
            for rec in report.reactive_compensation_recommendations:
                lines.append(f"  → {rec}")

        return "\n".join(lines)

    def _format_grid_codes(self, reports: list) -> str:
        lines: list = []
        lines.append("-" * 40)
        lines.append("GRID CODE INSPECTOR — IEEE 1547 Compliance")
        lines.append("-" * 40)
        lines.append("")

        for report in reports:
            status_icon = "✓" if report.overall_compliance == ComplianceResult.PASS else (
                "⚠" if report.overall_compliance == ComplianceResult.WARNING else "✗"
            )
            lines.append(
                f"  {status_icon} {report.package} "
                f"(Category {report.category.value}, "
                f"PF={report.power_factor:.2f})"
            )
            for check in report.checks:
                icon = "✓" if check.result == ComplianceResult.PASS else (
                    "⚠" if check.result == ComplianceResult.WARNING else "✗"
                )
                lines.append(f"    {icon} {check.name}: {check.details}")

        return "\n".join(lines)

    def _format_json(self, report: FullReport) -> str:
        """Format report as JSON."""
        data = {
            "project_path": report.project_path,
            "timestamp": report.timestamp.isoformat(),
            "overall_status": report.overall_status.value,
        }

        if report.n1_report:
            data["n1"] = {
                "total_packages": report.n1_report.total_packages,
                "passing_packages": report.n1_report.passing_packages,
                "compliance_score": report.n1_report.compliance_score,
                "spof_count": len(report.n1_report.spof_register),
                "spofs": [
                    {
                        "package": s.removed_package,
                        "blast_radius": s.blast_radius,
                        "state": s.system_state.value,
                        "recommendation": s.recommendation,
                    }
                    for s in report.n1_report.spof_register
                ],
            }

        if report.frequency_report:
            data["frequency"] = {
                "average_deviation": report.frequency_report.average_deviation,
                "worst_deviation": report.frequency_report.worst_deviation,
                "shocks": [
                    {
                        "package": r.shock.package,
                        "deviation": r.frequency_deviation,
                        "primary_recovery": r.primary_recovery,
                        "tertiary_needed": r.tertiary_needed,
                    }
                    for r in report.frequency_report.results
                ],
            }

        if report.opf_report:
            data["opf"] = {
                "total_risk": report.opf_report.total_risk,
                "congested": report.opf_report.congestion_bottlenecks,
                "overcoupled": [
                    {"source": s, "target": t}
                    for s, t in report.opf_report.overcoupled_pairs
                ],
            }

        if report.relay_report:
            data["relay"] = {
                "handler_count": len(report.relay_report.handlers),
                "cti_violations": len(report.relay_report.cti_violations),
                "blind_spots": report.relay_report.blind_spots,
                "tcc_overlaps": len(report.relay_report.tcc_overlaps),
            }

        if report.voltage_report:
            data["voltage"] = {
                "weakest": report.voltage_report.weakest_packages,
                "packages": [
                    {
                        "name": r.package,
                        "health_voltage": r.health_voltage,
                        "cpi": r.collapse_proximity_index,
                        "sagging": r.is_sagging,
                    }
                    for r in report.voltage_report.package_results
                ],
            }

        if report.grid_code_reports:
            data["grid_code"] = [
                {
                    "package": gc.package,
                    "category": gc.category.value,
                    "compliance": gc.overall_compliance.value,
                    "power_factor": gc.power_factor,
                }
                for gc in report.grid_code_reports
            ]

        return json.dumps(data, indent=2)
