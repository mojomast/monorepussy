"""Report generation for scan results — ported from unconformity."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .missing_models import ScanResult, Severity


_SEVERITY_SCORE = {
    Severity.LOW: 10,
    Severity.MEDIUM: 25,
    Severity.HIGH: 50,
    Severity.CRITICAL: 80,
}


def _risk_score(result: ScanResult) -> int:
    score = 0
    for item in result.unconformities:
        score += _SEVERITY_SCORE[item.severity]
    return min(100, score)


def render_report(result: ScanResult, fmt: str = "text", threshold: str | None = None) -> str:
    unconformities = result.unconformities
    if threshold:
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        min_index = order.index(Severity(threshold))
        unconformities = [u for u in unconformities if order.index(u.severity) >= min_index]
    if fmt == "json":
        payload = {
            "repo_path": result.repo_path,
            "scan_time": result.scan_time.isoformat(),
            "duration_seconds": result.duration_seconds,
            "total_commits_scanned": result.total_commits_scanned,
            "risk_score": _risk_score(result),
            "summary": Counter(u.type.value for u in unconformities),
            "findings": [asdict(u) for u in unconformities],
        }
        return json.dumps(payload, indent=2, default=str)
    summary = Counter(u.type.value for u in unconformities)
    lines = [
        f"Repository: {result.repo_path}",
        f"Risk score: {_risk_score(result)}",
        f"Commits scanned: {result.total_commits_scanned}",
        "Summary:",
    ]
    for key, value in sorted(summary.items()):
        lines.append(f"- {key}: {value}")
    lines.append("Findings:")
    for item in unconformities:
        lines.append(f"- {item.type.value} [{item.severity.value}]: {item.description}")
    if fmt == "markdown":
        return "\n".join(["# Unconformity Report", *lines])
    if fmt == "html":
        body = "".join(f"<li>{line}</li>" for line in lines)
        return f"<html><body><h1>Unconformity Report</h1><ul>{body}</ul></body></html>"
    return "\n".join(lines)


def write_report(path: str | None, content: str) -> None:
    if not path:
        print(content)
        return
    Path(path).write_text(content, encoding="utf-8")
