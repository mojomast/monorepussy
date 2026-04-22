"""Tests for DLO (Dead Letter Office) module."""

import json
import pytest
from pathlib import Path

from ussy_telegrapha.models import DLQEntry
from ussy_telegrapha.dlo import (
    compute_churn_rate,
    compute_health_score,
    classify_failure_taxonomy,
    find_systemic_source,
    load_dlq_entries,
    analyze_dlo,
    format_dlo_report,
    dlo_to_dict,
)


class TestComputeChurnRate:
    """Tests for churn rate computation."""

    def test_healthy_churn(self):
        churn = compute_churn_rate(10.0, 20.0)
        assert churn == pytest.approx(0.5)

    def test_steady_state(self):
        churn = compute_churn_rate(10.0, 10.0)
        assert churn == pytest.approx(1.0)

    def test_unhealthy_churn(self):
        churn = compute_churn_rate(47.0, 12.0)
        assert churn == pytest.approx(47.0 / 12.0)
        assert churn > 1.0

    def test_zero_resolution(self):
        churn = compute_churn_rate(10.0, 0.0)
        assert churn == float("inf")


class TestComputeHealthScore:
    """Tests for health score computation."""

    def test_healthy_system(self):
        score, status = compute_health_score(
            churn_rate=0.5,
            resolution_rate=20.0,
            accumulation_rate=10.0,
        )
        assert score >= 0.7
        assert status == "HEALTHY"

    def test_critical_system(self):
        score, status = compute_health_score(
            churn_rate=4.0,
            resolution_rate=5.0,
            accumulation_rate=20.0,
        )
        assert status == "CRITICAL"

    def test_zero_accumulation(self):
        score, status = compute_health_score(0.0, 0.0, 0.0)
        assert score == 1.0
        assert status == "HEALTHY"

    def test_with_aging(self):
        score_no_age, _ = compute_health_score(1.0, 10.0, 10.0, avg_age_hours=0.0)
        score_with_age, _ = compute_health_score(1.0, 10.0, 10.0, avg_age_hours=48.0)
        assert score_with_age < score_no_age


class TestClassifyFailureTaxonomy:
    """Tests for failure taxonomy classification."""

    def test_basic_taxonomy(self, sample_dlq_entries):
        taxonomy = classify_failure_taxonomy(sample_dlq_entries)
        assert "no_response" in taxonomy
        assert "destination_closed" in taxonomy
        assert "address_undecipherable" in taxonomy
        # Percentages should sum to 1.0
        total = sum(taxonomy.values())
        assert total == pytest.approx(1.0)

    def test_empty_entries(self):
        taxonomy = classify_failure_taxonomy([])
        assert taxonomy == {}

    def test_single_type(self):
        entries = [
            DLQEntry(id="1", failure_type="timeout"),
            DLQEntry(id="2", failure_type="timeout"),
        ]
        taxonomy = classify_failure_taxonomy(entries)
        assert taxonomy["timeout"] == pytest.approx(1.0)


class TestFindSystemicSource:
    """Tests for systemic source identification."""

    def test_with_entries(self, sample_dlq_entries):
        source, pct = find_systemic_source(sample_dlq_entries)
        assert source == "fraud-service"
        assert pct > 0.3

    def test_empty_entries(self):
        source, pct = find_systemic_source([])
        assert source == ""
        assert pct == 0.0

    def test_no_source(self):
        entries = [DLQEntry(id="1")]
        source, pct = find_systemic_source(entries)
        assert source == ""


class TestLoadDLQEntries:
    """Tests for DLQ file loading."""

    def test_load_valid_file(self, sample_dlq_json):
        entries = load_dlq_entries(sample_dlq_json)
        assert len(entries) == 20
        assert all(isinstance(e, DLQEntry) for e in entries)

    def test_load_first_entry_fields(self, sample_dlq_json):
        entries = load_dlq_entries(sample_dlq_json)
        first = entries[0]
        assert first.id == "msg-001"
        assert first.failure_type == "no_response"
        assert first.source_hop == "fraud-service"

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dlq_entries(tmp_path / "nonexistent.json")


class TestAnalyzeDLO:
    """Tests for full DLO analysis."""

    def test_basic_analysis(self, sample_dlq_entries):
        result = analyze_dlo(
            sample_dlq_entries,
            accumulation_rate=47.0,
            resolution_rate=12.0,
        )
        assert result.total_entries == 5
        assert result.accumulation_rate == 47.0
        assert result.resolution_rate == 12.0
        assert result.churn_rate > 1.0

    def test_systemic_source(self, sample_dlq_entries):
        result = analyze_dlo(sample_dlq_entries, accumulation_rate=10.0, resolution_rate=20.0)
        assert result.systemic_source == "fraud-service"

    def test_failure_taxonomy(self, sample_dlq_entries):
        result = analyze_dlo(sample_dlq_entries, accumulation_rate=10.0, resolution_rate=20.0)
        assert len(result.failure_taxonomy) > 0

    def test_unhealthy_recommendations(self, sample_dlq_entries):
        result = analyze_dlo(
            sample_dlq_entries,
            accumulation_rate=47.0,
            resolution_rate=12.0,
        )
        assert len(result.recommendations) > 0

    def test_empty_entries(self):
        result = analyze_dlo([], accumulation_rate=0.0, resolution_rate=0.0)
        assert result.total_entries == 0

    def test_default_rates(self, sample_dlq_entries):
        result = analyze_dlo(sample_dlq_entries)
        assert result.accumulation_rate > 0

    def test_destination_closed_reroute(self):
        """Test that destination_closed > 20% triggers re-route recommendation."""
        entries = [
            DLQEntry(id=f"m{i}", failure_type="destination_closed", source_hop="svc")
            for i in range(10)
        ]
        result = analyze_dlo(entries, accumulation_rate=10.0, resolution_rate=20.0)
        assert any("alternate" in r.lower() or "re-route" in r.lower()
                    for r in result.recommendations)


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_format(self, sample_dlq_entries):
        result = analyze_dlo(
            sample_dlq_entries,
            accumulation_rate=47.0,
            resolution_rate=12.0,
        )
        report = format_dlo_report(result)
        assert "Dead Letter Office" in report
        assert "Churn rate" in report

    def test_report_json_serializable(self, sample_dlq_entries):
        result = analyze_dlo(
            sample_dlq_entries,
            accumulation_rate=47.0,
            resolution_rate=12.0,
        )
        data = dlo_to_dict(result)
        json_str = json.dumps(data)
        assert json_str


class TestDLOToDict:
    """Tests for JSON serialization."""

    def test_dict_keys(self, sample_dlq_entries):
        result = analyze_dlo(
            sample_dlq_entries,
            accumulation_rate=47.0,
            resolution_rate=12.0,
        )
        data = dlo_to_dict(result)
        assert "total_entries" in data
        assert "churn_rate" in data
        assert "failure_taxonomy" in data
        assert "health_score" in data
        assert "health_status" in data
        assert "recommendations" in data
