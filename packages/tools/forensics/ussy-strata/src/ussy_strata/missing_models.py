"""Git forensics for what's MISSING — ported from unconformity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List


class UnconformityType(Enum):
    ANGULAR = "angular"
    DISCONFORMITY = "disconformity"
    NONCONFORMITY = "nonconformity"
    PARACONFORMITY = "paraconformity"
    BUTTRESS = "buttress"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class UnconformityEvent:
    type: UnconformityType
    severity: Severity
    description: str
    affected_commits: List[str]
    detected_at: datetime
    forensic_details: Dict[str, object] = field(default_factory=dict)
    geological_metaphor: str = ""


@dataclass(frozen=True)
class ScanResult:
    repo_path: str
    unconformities: List[UnconformityEvent]
    scan_time: datetime
    duration_seconds: float
    total_commits_scanned: int
