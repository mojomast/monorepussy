"""CLI Table output formatter."""

from stenography.models import ScanResult, Severity


_SEVERITY_COLOR = {
    Severity.CRITICAL: "\033[91m",  # Red
    Severity.HIGH: "\033[93m",      # Yellow
    Severity.MEDIUM: "\033[96m",    # Cyan
    Severity.LOW: "\033[37m",       # White
    Severity.INFO: "\033[90m",      # Gray
}
_RESET = "\033[0m"


class TableFormatter:
    """Formats scan results as a human-readable CLI table."""

    def __init__(self, color: bool = True):
        self.color = color

    def format(self, result: ScanResult) -> str:
        lines = []

        # Header
        lines.append(self._header())
        lines.append("")

        if not result.findings:
            lines.append("  ✅ No steganographic content detected.")
            lines.append("")
            lines.append(f"  Files scanned: {result.files_scanned}")
            return "\n".join(lines)

        # Summary bar
        by_severity = {}
        for f in result.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        summary_parts = []
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            if sev in by_severity:
                label = self._colorize(f"{sev.value}:{by_severity[sev]}", sev)
                summary_parts.append(label)

        lines.append(f"  Findings: {' | '.join(summary_parts)}")
        lines.append("")

        # Table header
        lines.append(f"  {'SEVERITY':<10} {'SCANNER':<14} {'FILE':<30} {'LINE':>5} {'COL':>4}  MESSAGE")
        lines.append(f"  {'─'*10} {'─'*14} {'─'*30} {'─'*5} {'─'*4}  {'─'*40}")

        # Group findings by file
        for finding in sorted(result.findings, key=lambda f: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(f.severity.value, 5),
            f.file, f.line
        )):
            sev_str = self._colorize(f"{finding.severity.value:<10}", finding.severity)
            file_short = finding.file
            if len(file_short) > 28:
                file_short = "…" + file_short[-27:]
            msg = finding.message
            if len(msg) > 60:
                msg = msg[:57] + "…"

            lines.append(
                f"  {sev_str} {finding.scanner:<14} {file_short:<30} "
                f"{finding.line:>5} {finding.column:>4}  {msg}"
            )

            # Add context line if available
            if finding.context_text:
                ctx = finding.context_text
                if len(ctx) > 70:
                    ctx = ctx[:67] + "…"
                lines.append(f"  {'':>10} {'':>14} {'':>30} {'':>5} {'':>4}  ↳ {ctx}")

        lines.append("")
        lines.append(f"  Total: {result.total_findings} findings in {result.files_scanned} files")
        return "\n".join(lines)

    def _header(self) -> str:
        return (
            "\n  ╔══════════════════════════════════════════════╗\n"
            "  ║          STENOGRAPHY — Scan Results          ║\n"
            "  ║     Steganographic Code Review Tool          ║\n"
            "  ╚══════════════════════════════════════════════╝"
        )

    def _colorize(self, text: str, severity: Severity) -> str:
        if not self.color:
            return text
        color = _SEVERITY_COLOR.get(severity, "")
        return f"{color}{text}{_RESET}"
