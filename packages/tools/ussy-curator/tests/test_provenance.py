"""Tests for curator.provenance."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from curator.provenance import MockCommit, ProvenanceTracker
from curator.storage import Storage


@pytest.fixture
def tracker() -> ProvenanceTracker:
    db = Storage()
    db.initialize()
    return ProvenanceTracker(db)


class TestMockCommit:
    def test_fields(self) -> None:
        c = MockCommit(
            hash="a" * 40,
            date=datetime.now(timezone.utc),
            author="test",
            file_path=Path("x.md"),
            lines_changed=10,
            lines_without_author_signature=2,
            parents=1,
        )
        assert c.hash == "a" * 40
        assert c.author == "test"


class TestProvenanceTracker:
    def test_accession_returns_number(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        num = tracker.accession(f, submitter="alice")
        assert num.startswith(str(datetime.now(timezone.utc).year))
        assert tracker.db.get_accession(f) == num

    def test_accession_sequence_increments(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("a")
        b.write_text("b")
        n1 = tracker.accession(a)
        n2 = tracker.accession(b)
        assert n1 != n2

    def test_build_provenance_chain(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        tracker.accession(f)
        chain = tracker.build_provenance_chain(f)
        assert "chain" in chain
        assert len(chain["chain"]) >= 1

    def test_chain_completeness(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        tracker.accession(f)
        chain = tracker.build_provenance_chain(f)
        assert 0.0 <= chain["completeness"] <= 1.0

    def test_find_gaps(self, tracker: ProvenanceTracker) -> None:
        chain = [
            {"date": "2023-01-01T00:00:00+00:00"},
            {"date": "2025-01-01T00:00:00+00:00"},
        ]
        gaps = tracker._find_gaps(chain)
        assert len(gaps) == 1
        assert gaps[0]["severity"] == "major"

    def test_no_gaps_short_interval(self, tracker: ProvenanceTracker) -> None:
        chain = [
            {"date": "2024-01-01T00:00:00+00:00"},
            {"date": "2024-02-01T00:00:00+00:00"},
        ]
        gaps = tracker._find_gaps(chain)
        assert len(gaps) == 0

    def test_classify_event_creation(self, tracker: ProvenanceTracker) -> None:
        c = MockCommit(hash="a" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("x"), lines_changed=10, lines_without_author_signature=0, parents=0)
        assert tracker._classify_event(c, None) == "creation"

    def test_classify_event_merge(self, tracker: ProvenanceTracker) -> None:
        c1 = MockCommit(hash="a" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("x"), lines_changed=10, lines_without_author_signature=0, parents=1)
        c2 = MockCommit(hash="b" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("x"), lines_changed=10, lines_without_author_signature=0, parents=2)
        assert tracker._classify_event(c2, c1) == "merge"

    def test_classify_event_move(self, tracker: ProvenanceTracker) -> None:
        c1 = MockCommit(hash="a" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("x"), lines_changed=10, lines_without_author_signature=0)
        c2 = MockCommit(hash="b" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("y"), lines_changed=10, lines_without_author_signature=0)
        assert tracker._classify_event(c2, c1) == "move"

    def test_attribution_confidence(self, tracker: ProvenanceTracker) -> None:
        c = MockCommit(hash="a" * 40, date=datetime.now(timezone.utc), author="a", file_path=Path("x"), lines_changed=10, lines_without_author_signature=2)
        conf = tracker._attribution_confidence(c)
        assert conf == pytest.approx(0.8)

    def test_line_of_custody_valid(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        tracker.accession(f)
        # Synthetic chain from fresh file usually passes
        assert tracker.line_of_custody_valid(f) is True

    def test_line_of_custody_invalid_missing(self, tracker: ProvenanceTracker, tmp_path: Path) -> None:
        f = tmp_path / "missing.md"
        assert tracker.line_of_custody_valid(f) is False
