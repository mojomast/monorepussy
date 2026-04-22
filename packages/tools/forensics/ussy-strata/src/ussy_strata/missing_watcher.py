"""Polling-based repository watcher — ported from unconformity."""

from __future__ import annotations

import json
import time
from typing import List

from .missing_scanner import scan_repository


def watch_repository(
    repo_path: str,
    interval: float = 30.0,
    webhook: str | None = None,
    iterations: int | None = None,
) -> List[dict]:
    seen = set()
    events: List[dict] = []
    count = 0
    while iterations is None or count < iterations:
        result = scan_repository(repo_path)
        for item in result.unconformities:
            payload = {
                "type": item.type.value,
                "severity": item.severity.value,
                "description": item.description,
                "affected_commits": item.affected_commits,
                "detected_at": item.detected_at.isoformat(),
            }
            key = json.dumps(payload, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            events.append(payload)
        count += 1
        if iterations is not None and count >= iterations:
            break
        time.sleep(interval)
    return events
