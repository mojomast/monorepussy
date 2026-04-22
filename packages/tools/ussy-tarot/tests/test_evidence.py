"""Tests for tarot.evidence module."""

import json
import os
import tempfile
import pytest

from tarot.evidence import EvidenceCollector, EvidenceItem, IncidentRecord
from tests.conftest import create_incidents_file


class TestEvidenceItem:
    def test_creation(self):
        item = EvidenceItem(source="git", adr_id="ADR-001", description="Test evidence")
        assert item.source == "git"
        assert item.adr_id == "ADR-001"
        assert item.relevance == 1.0

    def test_auto_timestamp(self):
        item = EvidenceItem(source="git", adr_id="ADR-001", description="Test")
        assert item.timestamp != ""

    def test_relevance_clamped(self):
        item = EvidenceItem(source="git", adr_id="ADR-001", description="Test", relevance=2.0)
        assert item.relevance == 1.0

    def test_relevance_clamped_negative(self):
        item = EvidenceItem(source="git", adr_id="ADR-001", description="Test", relevance=-1.0)
        assert item.relevance == 0.0


class TestIncidentRecord:
    def test_creation(self):
        inc = IncidentRecord(incident_id="INC-001", title="Outage")
        assert inc.incident_id == "INC-001"
        assert inc.severity == "medium"
        assert inc.affected_adrs == []

    def test_auto_timestamp(self):
        inc = IncidentRecord(incident_id="INC-001", title="Outage")
        assert inc.timestamp != ""


class TestEvidenceCollector:
    def test_add_evidence(self):
        collector = EvidenceCollector()
        collector.add_evidence(EvidenceItem(source="git", adr_id="ADR-001", description="Test"))
        assert len(collector.evidence) == 1

    def test_add_incident(self):
        collector = EvidenceCollector()
        collector.add_incident(IncidentRecord(
            incident_id="INC-001",
            title="Outage",
            severity="high",
            affected_adrs=["ADR-001", "ADR-002"],
        ))
        assert len(collector.incidents) == 1
        # Should auto-create evidence for each affected ADR
        assert len(collector.evidence) == 2

    def test_load_incidents_from_json(self):
        filepath = create_incidents_file()
        try:
            collector = EvidenceCollector()
            collector.load_incidents_from_json(filepath)
            assert len(collector.incidents) == 3
            assert collector.incidents[0].incident_id == "INC-001"
        finally:
            os.unlink(filepath)

    def test_get_evidence_for_card(self):
        collector = EvidenceCollector()
        collector.add_evidence(EvidenceItem(source="git", adr_id="ADR-001", description="Test 1"))
        collector.add_evidence(EvidenceItem(source="incident", adr_id="ADR-001", description="Test 2"))
        collector.add_evidence(EvidenceItem(source="git", adr_id="ADR-002", description="Test 3"))
        evidence = collector.get_evidence_for_card("ADR-001")
        assert len(evidence) == 2

    def test_get_evidence_for_card_case_insensitive(self):
        collector = EvidenceCollector()
        collector.add_evidence(EvidenceItem(source="git", adr_id="adr-001", description="Test"))
        evidence = collector.get_evidence_for_card("ADR-001")
        assert len(evidence) == 1

    def test_get_incidents_for_card(self):
        collector = EvidenceCollector()
        collector.add_incident(IncidentRecord(
            incident_id="INC-001",
            title="Outage",
            severity="critical",
            affected_adrs=["ADR-001"],
        ))
        incidents = collector.get_incidents_for_card("ADR-001")
        assert len(incidents) == 1

    def test_compute_incident_correlation(self):
        collector = EvidenceCollector()
        collector.add_incident(IncidentRecord(
            incident_id="INC-001",
            title="Outage",
            severity="critical",
            affected_adrs=["ADR-001"],
        ))
        correlation = collector.compute_incident_correlation("ADR-001")
        assert correlation > 0.0
        assert correlation <= 1.0

    def test_compute_incident_correlation_no_incidents(self):
        collector = EvidenceCollector()
        correlation = collector.compute_incident_correlation("ADR-001")
        assert correlation == 0.0

    def test_evidence_summary(self):
        collector = EvidenceCollector()
        collector.add_evidence(EvidenceItem(source="git", adr_id="ADR-001", description="Test", relevance=0.8))
        collector.add_incident(IncidentRecord(
            incident_id="INC-001",
            title="Outage",
            severity="high",
            affected_adrs=["ADR-001"],
        ))
        summary = collector.evidence_summary("ADR-001")
        assert summary["adr_id"] == "ADR-001"
        assert summary["evidence_count"] >= 1
        assert summary["incident_count"] == 1
        assert summary["incident_correlation"] > 0.0
        assert "git" in summary["sources"] or "incident" in summary["sources"]

    def test_analyze_git_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock git log
            with open(os.path.join(tmpdir, "git_log.txt"), "w") as f:
                f.write("Fix session handling in ADR-001\n")
                f.write("Update caching per ADR-003\n")
                f.write("Unrelated commit\n")
            collector = EvidenceCollector()
            items = collector.analyze_git_history(tmpdir, "ADR-001")
            assert len(items) >= 1
            assert any("ADR-001" in i.description for i in items)

    def test_load_blog_entries(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{
                "title": "Why We Chose PostgreSQL",
                "content": "After evaluating ADR-001, we decided on PostgreSQL...",
                "url": "https://blog.example.com/postgres",
            }], f)
            filepath = f.name

        try:
            collector = EvidenceCollector()
            collector.load_blog_entries(filepath)
            assert len(collector.blog_entries) == 1
            # Should have created evidence for ADR-001 reference
            assert len(collector.evidence) >= 1
        finally:
            os.unlink(filepath)
