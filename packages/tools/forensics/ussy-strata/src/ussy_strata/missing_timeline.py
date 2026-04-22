"""Timeline visualization — ported from unconformity."""

from __future__ import annotations

from .missing_models import ScanResult


def render_timeline(result: ScanResult, width: int = 80) -> str:
    commits = max(1, result.total_commits_scanned)
    span = max(1, min(width, commits))
    bars = ["■" for _ in range(span)]
    lines = ["Timeline:", "".join(bars)]
    for item in sorted(result.unconformities, key=lambda event: event.detected_at):
        glyph = {
            "angular": "▲",
            "disconformity": "═",
            "nonconformity": "✕",
            "paraconformity": "╌",
            "buttress": "▤",
        }.get(item.type.value, "?")
        lines.append(f"{glyph} {item.type.value} [{item.severity.value}] {item.description}")
        if item.affected_commits:
            lines.append(f"  commits: {', '.join(item.affected_commits[:3])}")
    if result.unconformities:
        lines.append(
            "Legend: ■ history | ▲ angular | ═ disconformity | ✕ nonconformity | ╌ paraconformity | ▤ buttress"
        )
    else:
        lines.append("Legend: ■ continuous history")
    return "\n".join(lines)
