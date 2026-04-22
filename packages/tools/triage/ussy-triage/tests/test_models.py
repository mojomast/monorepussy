"""Tests for the data models."""

import pytest
from triage.models import (
    VictimType, Confidence, ErrorPattern, GitContext,
    HistoryMatch, EnrichedError, Diagnosis
)


class TestVictimType:
    """Tests for VictimType enum."""

    def test_values(self):
        assert VictimType.BUILD.value == "build"
        assert VictimType.TEST.value == "test"
        assert VictimType.RUNTIME.value == "runtime"
        assert VictimType.DEPLOYMENT.value == "deployment"
        assert VictimType.UNKNOWN.value == "unknown"

    def test_from_value(self):
        assert VictimType("build") == VictimType.BUILD


class TestConfidence:
    """Tests for Confidence enum."""

    def test_values(self):
        assert Confidence.HIGH.value == "high"
        assert Confidence.MEDIUM.value == "medium"
        assert Confidence.LOW.value == "low"


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_creation(self):
        p = ErrorPattern(
            pattern_type="python_error",
            language="python",
            root_cause="Module not found",
            fix_template="pip install it",
            confidence=0.9,
        )
        assert p.pattern_type == "python_error"
        assert p.language == "python"
        assert p.root_cause == "Module not found"
        assert p.fix_template == "pip install it"
        assert p.confidence == 0.9
        assert p.matched_text == ""

    def test_with_matched_text(self):
        p = ErrorPattern(
            pattern_type="rust_compile",
            language="rust",
            root_cause="Missing impl",
            fix_template="Add impl",
            confidence=0.85,
            matched_text="trait `Foo` not implemented",
        )
        assert p.matched_text == "trait `Foo` not implemented"


class TestGitContext:
    """Tests for GitContext dataclass."""

    def test_default_values(self):
        ctx = GitContext()
        assert ctx.author is None
        assert ctx.commit_hash is None
        assert ctx.commit_message is None
        assert ctx.commit_date is None
        assert ctx.recent_commits == []

    def test_with_values(self):
        ctx = GitContext(
            author="Alice",
            commit_hash="abc123",
            commit_message="Fix bug",
            recent_commits=[{"hash": "def456", "message": "Old commit"}],
        )
        assert ctx.author == "Alice"
        assert ctx.commit_hash == "abc123"
        assert len(ctx.recent_commits) == 1


class TestHistoryMatch:
    """Tests for HistoryMatch dataclass."""

    def test_creation(self):
        hm = HistoryMatch(
            commit_hash="abc123",
            commit_message="Fixed ImportError",
            fix_description="Added missing import",
            similarity=0.85,
        )
        assert hm.commit_hash == "abc123"
        assert hm.similarity == 0.85

    def test_defaults(self):
        hm = HistoryMatch(commit_hash="abc", commit_message="test")
        assert hm.fix_description == ""
        assert hm.similarity == 0.0


class TestEnrichedError:
    """Tests for EnrichedError dataclass."""

    def test_basic_creation(self):
        err = EnrichedError(line_number=10, content="Error: bad")
        assert err.line_number == 10
        assert err.victim_type == VictimType.UNKNOWN
        assert err.matched_pattern is None
        assert err.git_context is None
        assert err.history_matches == []

    def test_full_context(self):
        err = EnrichedError(
            line_number=5,
            content="middle",
            context_before=["a", "b"],
            context_after=["c"],
        )
        assert err.full_context == ["a", "b", "middle", "c"]

    def test_to_dict_basic(self):
        err = EnrichedError(
            line_number=42,
            content="ValueError: bad",
            error_type="python_error",
            language="python",
            file_path="app.py",
            line_in_file=10,
            severity="error",
            victim_type=VictimType.RUNTIME,
        )
        d = err.to_dict()
        assert d["line_number"] == 42
        assert d["error_type"] == "python_error"
        assert d["victim_type"] == "runtime"
        assert "pattern" not in d  # No matched pattern

    def test_to_dict_with_pattern(self):
        pattern = ErrorPattern(
            pattern_type="python_error",
            language="python",
            root_cause="Module not found",
            fix_template="Install it",
            confidence=0.9,
        )
        err = EnrichedError(
            line_number=1,
            content="Error",
            matched_pattern=pattern,
        )
        d = err.to_dict()
        assert "pattern" in d
        assert d["pattern"]["type"] == "python_error"

    def test_to_dict_with_git_context(self):
        git = GitContext(author="Bob", commit_hash="abc")
        err = EnrichedError(
            line_number=1,
            content="Error",
            git_context=git,
        )
        d = err.to_dict()
        assert "git" in d
        assert d["git"]["author"] == "Bob"

    def test_to_dict_with_history(self):
        hist = HistoryMatch(commit_hash="def", commit_message="fix", similarity=0.8)
        err = EnrichedError(
            line_number=1,
            content="Error",
            history_matches=[hist],
        )
        d = err.to_dict()
        assert "history" in d
        assert len(d["history"]) == 1


class TestDiagnosis:
    """Tests for Diagnosis dataclass."""

    def test_creation(self):
        d = Diagnosis(
            case_number=1,
            suspect="ValueError in app.py",
            victim=VictimType.RUNTIME,
            evidence=["Line 42: ValueError: bad"],
            motive="Invalid input",
            witness_testimony=[],
            recommended_action="Fix the input",
            confidence=Confidence.HIGH,
            confidence_score=0.9,
        )
        assert d.case_number == 1
        assert d.suspect == "ValueError in app.py"
        assert d.victim == VictimType.RUNTIME
        assert d.confidence == Confidence.HIGH

    def test_to_dict(self):
        d = Diagnosis(
            case_number=3,
            suspect="Rust compile error",
            victim=VictimType.BUILD,
            evidence=["Line 1: error[E0433]"],
            motive="Missing import",
            witness_testimony=["Last modified by Alice"],
            recommended_action="Add the missing crate",
            confidence=Confidence.MEDIUM,
            confidence_score=0.65,
        )
        result = d.to_dict()
        assert result["case_number"] == 3
        assert result["victim"] == "build"
        assert result["confidence"] == "medium"
        assert result["confidence_score"] == 0.65
