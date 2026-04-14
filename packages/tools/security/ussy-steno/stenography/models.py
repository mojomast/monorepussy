"""Data models for scan findings."""

import enum
from dataclasses import dataclass, field
from typing import Optional


class Severity(enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Context(enum.Enum):
    IDENTIFIER = "identifier"
    STRING_LITERAL = "string_literal"
    COMMENT = "comment"
    WHITESPACE = "whitespace"
    OTHER = "other"


SEVERITY_MAP = {
    Context.IDENTIFIER: Severity.CRITICAL,
    Context.STRING_LITERAL: Severity.HIGH,
    Context.COMMENT: Severity.MEDIUM,
    Context.WHITESPACE: Severity.LOW,
    Context.OTHER: Severity.INFO,
}


@dataclass
class Finding:
    """A single steganographic detection finding."""

    scanner: str
    file: str
    line: int
    column: int
    severity: Severity
    context: Context
    message: str
    char_code: Optional[str] = None
    character: Optional[str] = None
    context_text: Optional[str] = None
    rule_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "scanner": self.scanner,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity.value,
            "context": self.context.value,
            "message": self.message,
            "char_code": self.char_code,
            "character": self.character,
            "context_text": self.context_text,
            "rule_id": self.rule_id,
        }


@dataclass
class ScanResult:
    """Aggregated result from all scanners."""

    findings: list = field(default_factory=list)
    files_scanned: int = 0
    total_findings: int = 0
    _seen: set = field(default_factory=set, repr=False, compare=False)

    def add(self, finding: Finding):
        """Add a finding, deduplicating by (file, line, column, rule_id)."""
        dedup_key = (finding.file, finding.line, finding.column, finding.rule_id)
        if dedup_key in self._seen:
            return
        self._seen.add(dedup_key)
        self.findings.append(finding)
        self.total_findings += 1

    def merge(self, other: "ScanResult"):
        for f in other.findings:
            self.add(f)
        self.files_scanned += other.files_scanned

    def to_dict(self) -> dict:
        return {
            "files_scanned": self.files_scanned,
            "total_findings": self.total_findings,
            "findings": [f.to_dict() for f in self.findings],
        }
