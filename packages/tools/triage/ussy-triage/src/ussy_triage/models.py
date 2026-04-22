"""Data models for Triage's diagnostic pipeline."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VictimType(Enum):
    """What failed — the 'victim' in the crime scene."""
    BUILD = "build"
    TEST = "test"
    RUNTIME = "runtime"
    DEPLOYMENT = "deployment"
    LINT = "lint"
    UNKNOWN = "unknown"


class Confidence(Enum):
    """How confident is the diagnosis."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorPattern:
    """A matched error pattern from the database."""
    pattern_type: str
    language: Optional[str]
    root_cause: str
    fix_template: str
    confidence: float
    matched_text: str = ""


@dataclass
class GitContext:
    """Git context for the error location."""
    author: Optional[str] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    commit_date: Optional[str] = None
    recent_commits: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class HistoryMatch:
    """A match from project history for similar errors."""
    commit_hash: str
    commit_message: str
    fix_description: str = ""
    similarity: float = 0.0


@dataclass
class EnrichedError:
    """An error enriched with context, patterns, and history."""
    # Core error info
    line_number: int
    content: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    error_type: str = "unknown"
    language: Optional[str] = None
    file_path: Optional[str] = None
    line_in_file: Optional[int] = None
    severity: str = "error"

    # Enrichment
    victim_type: VictimType = VictimType.UNKNOWN
    matched_pattern: Optional[ErrorPattern] = None
    git_context: Optional[GitContext] = None
    history_matches: List[HistoryMatch] = field(default_factory=list)

    @property
    def full_context(self) -> List[str]:
        return self.context_before + [self.content] + self.context_after

    def to_dict(self) -> dict:
        result = {
            "line_number": self.line_number,
            "content": self.content,
            "error_type": self.error_type,
            "language": self.language,
            "file_path": self.file_path,
            "line_in_file": self.line_in_file,
            "severity": self.severity,
            "victim_type": self.victim_type.value,
        }
        if self.matched_pattern:
            result["pattern"] = {
                "type": self.matched_pattern.pattern_type,
                "root_cause": self.matched_pattern.root_cause,
                "fix_template": self.matched_pattern.fix_template,
                "confidence": self.matched_pattern.confidence,
            }
        if self.git_context:
            result["git"] = {
                "author": self.git_context.author,
                "commit": self.git_context.commit_hash,
                "message": self.git_context.commit_message,
            }
        if self.history_matches:
            result["history"] = [
                {"commit": m.commit_hash, "message": m.commit_message,
                 "similarity": m.similarity}
                for m in self.history_matches
            ]
        return result


@dataclass
class Diagnosis:
    """A complete diagnosis of an error."""
    # The crime scene
    case_number: int
    suspect: str
    victim: VictimType
    evidence: List[str]
    motive: str
    witness_testimony: List[str]
    recommended_action: str
    confidence: Confidence
    confidence_score: float

    # Raw data
    enriched_error: Optional[EnrichedError] = None

    def to_dict(self) -> dict:
        return {
            "case_number": self.case_number,
            "suspect": self.suspect,
            "victim": self.victim.value,
            "evidence": self.evidence,
            "motive": self.motive,
            "witness_testimony": self.witness_testimony,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
        }
