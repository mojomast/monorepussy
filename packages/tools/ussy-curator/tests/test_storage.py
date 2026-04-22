"""Tests for curator.storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_curator.storage import Storage


@pytest.fixture
def storage() -> Storage:
    db = Storage()
    db.initialize()
    yield db
    db.close()


class TestAccessionRegistry:
    def test_next_acquisition_sequence(self, storage: Storage) -> None:
        assert storage.next_acquisition_sequence(2024) == 1
        storage.record_accession({
            "accession_number": "2024.001.001",
            "path": "/tmp/a.md",
            "submitter": "test",
            "date": "2024-01-01",
            "origin": "internal",
            "status": "accessioned",
        })
        assert storage.next_acquisition_sequence(2024) == 2

    def test_get_accession(self, storage: Storage) -> None:
        storage.record_accession({
            "accession_number": "2024.001.001",
            "path": "/tmp/a.md",
            "submitter": "test",
            "date": "2024-01-01",
            "origin": "internal",
            "status": "accessioned",
        })
        assert storage.get_accession(Path("/tmp/a.md")) == "2024.001.001"

    def test_get_accession_missing(self, storage: Storage) -> None:
        assert storage.get_accession(Path("/tmp/missing.md")) is None

    def test_get_accession_by_number(self, storage: Storage) -> None:
        storage.record_accession({
            "accession_number": "2024.001.001",
            "path": "/tmp/a.md",
            "submitter": "test",
            "date": "2024-01-01",
            "origin": "internal",
            "status": "accessioned",
        })
        row = storage.get_accession_by_number("2024.001.001")
        assert row is not None
        assert row["path"] == "/tmp/a.md"


class TestMARCRecords:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_marc_record(Path("/tmp/a.md"), {"245": "Title"}, 0.8)
        record = storage.get_marc_record(Path("/tmp/a.md"))
        assert record is not None
        assert record["fields"]["245"] == "Title"
        assert record["completeness_score"] == pytest.approx(0.8)

    def test_get_missing(self, storage: Storage) -> None:
        assert storage.get_marc_record(Path("/tmp/missing.md")) is None


class TestClassification:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_classification(Path("/tmp/a.md"), "000:AUD:general", "000", {"AUD": "general"})
        row = storage.get_classification(Path("/tmp/a.md"))
        assert row is not None
        assert row["notation"] == "000:AUD:general"
        assert row["facets"]["AUD"] == "general"


class TestConservation:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_conservation_report(Path("/tmp/a.md"), {
            "metrics": {"age_days": 10},
            "deterioration_rate": 0.01,
            "condition_index": 95.0,
            "grade": "Excellent",
            "treatment": "None",
        })
        row = storage.get_conservation_report(Path("/tmp/a.md"))
        assert row is not None
        assert row["grade"] == "Excellent"
        assert row["condition_index"] == pytest.approx(95.0)


class TestProvenance:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_provenance_chain(Path("/tmp/a.md"), {
            "accession_number": "2024.001.001",
            "chain": [{"event_id": "abc12345"}],
            "completeness": 0.9,
            "gaps": [],
        })
        row = storage.get_provenance_chain(Path("/tmp/a.md"))
        assert row is not None
        assert row["completeness"] == pytest.approx(0.9)


class TestExhibitions:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_exhibition({
            "name": "Onboarding",
            "theme": "getting started",
            "audience_profile": {"level": "beginner"},
            "max_items": 10,
            "selection": ["/tmp/a.md"],
        })
        row = storage.get_exhibition("Onboarding")
        assert row is not None
        assert row["theme"] == "getting started"


class TestWeeding:
    def test_save_and_get(self, storage: Storage) -> None:
        storage.save_weeding_proposal({
            "path": "/tmp/a.md",
            "accession_number": "2024.001.001",
            "title": "Old Doc",
            "weed_score": 0.75,
            "triggered_criteria": ["Superseded"],
            "justification": "Old",
            "impact_assessment": {},
            "disposition": "archive",
            "ethical_review": True,
        })
        row = storage.get_weeding_proposal(Path("/tmp/a.md"))
        assert row is not None
        assert row["weed_score"] == pytest.approx(0.75)
        assert row["ethical_review"] is True

    def test_list_weeding_proposals(self, storage: Storage) -> None:
        storage.save_weeding_proposal({
            "path": "/tmp/a.md",
            "accession_number": "2024.001.001",
            "title": "A",
            "weed_score": 0.9,
            "triggered_criteria": [],
            "justification": "",
            "impact_assessment": {},
            "disposition": "remove",
            "ethical_review": False,
        })
        storage.save_weeding_proposal({
            "path": "/tmp/b.md",
            "accession_number": "2024.001.002",
            "title": "B",
            "weed_score": 0.5,
            "triggered_criteria": [],
            "justification": "",
            "impact_assessment": {},
            "disposition": "remove",
            "ethical_review": False,
        })
        rows = storage.list_weeding_proposals()
        assert len(rows) == 2
        assert rows[0]["weed_score"] > rows[1]["weed_score"]
