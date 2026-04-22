"""Tests for the DiagnosisRenderer module."""

import json
import pytest
from ussy_triage.renderer import DiagnosisRenderer
from ussy_triage.models import (
    Diagnosis, EnrichedError, ErrorPattern, GitContext,
    HistoryMatch, VictimType, Confidence
)


def make_enriched_error(**kwargs):
    """Helper to create an EnrichedError with defaults."""
    defaults = {
        "line_number": 1,
        "content": "ValueError: invalid input",
        "error_type": "python_error",
        "language": "python",
        "severity": "error",
        "victim_type": VictimType.RUNTIME,
    }
    defaults.update(kwargs)
    return EnrichedError(**defaults)


def make_pattern(**kwargs):
    """Helper to create an ErrorPattern with defaults."""
    defaults = {
        "pattern_type": "python_error",
        "language": "python",
        "root_cause": "Invalid input provided",
        "fix_template": "Validate input before processing",
        "confidence": 0.85,
    }
    defaults.update(kwargs)
    return ErrorPattern(**defaults)


class TestDiagnosisRenderer:
    """Tests for the DiagnosisRenderer class."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_diagnose_basic(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        assert isinstance(diag, Diagnosis)
        assert diag.case_number == 1
        assert diag.suspect != ""
        assert len(diag.evidence) > 0
        assert diag.motive != ""
        assert diag.recommended_action != ""

    def test_case_counter_increments(self):
        err = make_enriched_error()
        d1 = self.renderer.diagnose(err)
        d2 = self.renderer.diagnose(err)
        assert d1.case_number == 1
        assert d2.case_number == 2

    def test_diagnose_with_pattern(self):
        pattern = make_pattern()
        err = make_enriched_error(matched_pattern=pattern)
        diag = self.renderer.diagnose(err)
        assert "Invalid input" in diag.suspect or "ValueError" in diag.suspect

    def test_diagnose_all(self):
        errors = [
            make_enriched_error(line_number=1, content="Error 1"),
            make_enriched_error(line_number=2, content="Error 2"),
        ]
        diags = self.renderer.diagnose_all(errors)
        assert len(diags) == 2
        assert diags[0].case_number != diags[1].case_number


class TestDetectiveRender:
    """Tests for the detective report renderer."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_render_detective(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="detective")
        assert "CRIME SCENE" in output
        assert "SUSPECT" in output
        assert "EVIDENCE" in output
        assert "MOTIVE" in output
        assert "RECOMMENDED ACTION" in output
        assert "CASE CLOSED" in output

    def test_render_detective_with_pattern(self):
        pattern = make_pattern(
            root_cause="Module not installed",
            fix_template="Run pip install",
        )
        err = make_enriched_error(matched_pattern=pattern)
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="detective")
        assert "Module not installed" in output
        assert "Run pip install" in output

    def test_render_detective_with_witness(self):
        git = GitContext(author="Alice", commit_hash="abc123", commit_message="Fix bug")
        err = make_enriched_error(git_context=git)
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="detective")
        assert "WITNESS TESTIMONY" in output
        assert "Alice" in output

    def test_render_detective_no_witness(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="detective")
        # Without git context, witness section may or may not appear
        assert "CRIME SCENE" in output


class TestJsonRender:
    """Tests for the JSON renderer."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_render_json(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="json")
        data = json.loads(output)
        assert "case_number" in data
        assert "suspect" in data
        assert "evidence" in data
        assert "confidence" in data

    def test_json_confidence_values(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="json")
        data = json.loads(output)
        assert data["confidence"] in ("high", "medium", "low")
        assert 0 <= data["confidence_score"] <= 1


class TestMinimalRender:
    """Tests for the minimal renderer."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_render_minimal(self):
        err = make_enriched_error(file_path="app.py", line_in_file=42)
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="minimal")
        assert "app.py" in output
        assert "42" in output

    def test_render_minimal_no_file(self):
        err = make_enriched_error()
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="minimal")
        assert "confidence" in output.lower()


class TestTeachingRender:
    """Tests for the teaching renderer."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_render_teaching_python(self):
        pattern = make_pattern()
        err = make_enriched_error(
            error_type="python_error",
            matched_pattern=pattern,
        )
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="teaching")
        assert "LEARN MORE" in output
        assert "CRIME SCENE" in output  # Includes the detective report

    def test_render_teaching_rust(self):
        pattern = make_pattern(pattern_type="rust_compile", language="rust")
        err = make_enriched_error(
            error_type="rust_compile",
            language="rust",
            matched_pattern=pattern,
        )
        diag = self.renderer.diagnose(err)
        output = self.renderer.render(diag, format="teaching")
        assert "LEARN MORE" in output


class TestRenderAll:
    """Tests for rendering multiple diagnoses."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_render_all_detective(self):
        errors = [
            make_enriched_error(line_number=1, content="Error 1"),
            make_enriched_error(line_number=2, content="Error 2"),
        ]
        diags = self.renderer.diagnose_all(errors)
        output = self.renderer.render_all(diags, format="detective")
        assert output.count("CRIME SCENE") == 2

    def test_render_all_empty(self):
        output = self.renderer.render_all([], format="detective")
        assert "No errors found" in output

    def test_render_all_json(self):
        errors = [
            make_enriched_error(line_number=1, content="Error 1"),
        ]
        diags = self.renderer.diagnose_all(errors)
        output = self.renderer.render_all(diags, format="json")
        # JSON output should be parseable (array format)
        data = json.loads(output)
        assert isinstance(data, list) and len(data) > 0
        assert "case_number" in data[0]


class TestConfidenceComputation:
    """Tests for confidence scoring."""

    def setup_method(self):
        self.renderer = DiagnosisRenderer()

    def test_base_confidence_low(self):
        err = make_enriched_error(
            error_type="unknown_type",
            language=None,
            file_path=None,
        )
        diag = self.renderer.diagnose(err)
        # Without pattern, language, or git, confidence should be low
        assert diag.confidence == Confidence.LOW
        assert diag.confidence_score < 0.5

    def test_pattern_boosts_confidence(self):
        pattern = make_pattern(confidence=0.9)
        err = make_enriched_error(matched_pattern=pattern)
        diag = self.renderer.diagnose(err)
        assert diag.confidence_score >= 0.8

    def test_language_boosts_confidence(self):
        err = make_enriched_error(language="python")
        diag = self.renderer.diagnose(err)
        # Language detection adds a small boost
        assert diag.confidence_score >= 0.3

    def test_file_path_boosts_confidence(self):
        err = make_enriched_error(file_path="app.py")
        diag = self.renderer.diagnose(err)
        # File path adds a small boost
        assert diag.confidence_score >= 0.3

    def test_high_confidence_classification(self):
        pattern = make_pattern(confidence=0.95)
        git = GitContext(author="Alice", commit_hash="abc")
        err = make_enriched_error(
            matched_pattern=pattern,
            language="python",
            file_path="app.py",
            line_in_file=10,
            git_context=git,
        )
        diag = self.renderer.diagnose(err)
        assert diag.confidence == Confidence.HIGH
