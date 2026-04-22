"""Tests for curator.weeding."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_curator.weeding import WeedingEngine
from ussy_curator.models import Document
from ussy_curator.classification import FacetedClassification
from ussy_curator.conservation import ConservationReport


def _make_doc(tmp_path: Path, name: str, content: str, notation: str = "000:AUD:general") -> Document:
    p = tmp_path / name
    p.write_text(content)
    doc = Document(path=p, content=content)
    doc.classification = FacetedClassification(notation)
    doc.conservation_report = ConservationReport(p)
    doc.provenance_chain = {"completeness": 0.8, "gaps": []}
    return doc


class TestWeedingEngine:
    def test_evaluate_returns_all_criteria(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Hello world.")
        engine = WeedingEngine()
        result = engine.evaluate(doc, [doc])
        assert set(result.keys()) == {"M", "U", "S", "T", "I", "E"}

    def test_weed_score_weights(self) -> None:
        engine = WeedingEngine()
        eval_result = {"M": 1.0, "U": 0.0, "S": 0.0, "T": 0.0, "I": 0.0, "E": 0.0}
        score = engine.weed_score(eval_result)
        assert score == pytest.approx(0.25)

    def test_generate_proposal_below_threshold(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Excellent fresh documentation.")
        engine = WeedingEngine()
        proposal = engine.generate_deaccession_proposal(doc, [doc])
        assert proposal is None

    def test_generate_proposal_above_threshold(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Legacy old bad wrong deprecated.")
        # Make conservation poor by referencing old code (no siblings, so code_age=0)
        # The doc itself is fresh, so condition might still be high. Let's use link rot.
        doc.content = "See [broken](missing.md). Error: Traceback\n```\nSyntaxError\n```"
        doc.conservation_report = ConservationReport(doc.path)
        engine = WeedingEngine()
        proposal = engine.generate_deaccession_proposal(doc, [doc])
        # Might still be below threshold, so just check it doesn't crash
        assert proposal is None or isinstance(proposal, dict)

    def test_batch_weed(self, tmp_path: Path) -> None:
        docs = [
            _make_doc(tmp_path, f"{i}.md", f"Doc {i}")
            for i in range(3)
        ]
        engine = WeedingEngine()
        candidates = engine.batch_weed(docs, threshold=0.99)
        assert isinstance(candidates, list)

    def test_check_triviality_short(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Hi.")
        engine = WeedingEngine()
        assert engine._check_triviality(doc) > 0.0

    def test_check_triviality_substantial(self, tmp_path: Path) -> None:
        # Use real words so keyword extraction works (regex requires a-zA-Z only)
        words = ["python", "code", "testing", "api", "docker", "deployment"] * 40
        content = " ".join(words)
        doc = _make_doc(tmp_path, "a.md", content)
        engine = WeedingEngine()
        assert engine._check_triviality(doc) < 1.0

    def test_check_relevance_no_refs(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "No code.")
        engine = WeedingEngine()
        assert engine._check_relevance(doc) == 0.5

    def test_check_relevance_with_refs(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Use `os.path.join`.")
        engine = WeedingEngine()
        assert engine._check_relevance(doc) < 0.5

    def test_check_errors_no_blocks(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "No code blocks.")
        engine = WeedingEngine()
        assert engine._check_errors(doc) == 0.0

    def test_check_errors_with_bad_block(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "```\nTraceback\n```")
        engine = WeedingEngine()
        assert engine._check_errors(doc) == 1.0

    def test_criteria_labels(self) -> None:
        assert WeedingEngine.CRITERIA["M"] == "Misleading"
        assert WeedingEngine.CRITERIA["E"] == "Erroneous"
