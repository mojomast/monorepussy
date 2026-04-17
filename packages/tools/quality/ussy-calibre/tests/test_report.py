"""Tests for the report generator."""

from datetime import datetime, timezone, timedelta

import pytest

from calibre.models import (
    CapabilitySpec,
    DriftObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
)
from calibre.report import generate_full_report


class TestGenerateFullReport:
    def test_basic_report(self, sample_test_runs):
        report = generate_full_report("test_suite", sample_test_runs)
        assert "METROLOGICAL CHARACTERIZATION REPORT" in report
        assert "Uncertainty Budget" in report
        assert "Gauge R&R" in report
        assert "Capability Analysis" in report
        assert "SUMMARY" in report

    def test_report_with_drift(self, sample_test_runs, sample_drift_observations):
        report = generate_full_report(
            "test_suite", sample_test_runs,
            drift_observations=sample_drift_observations,
        )
        assert "Drift Analysis" in report

    def test_report_with_traceability(self, sample_test_runs, sample_traceability_links):
        report = generate_full_report(
            "test_suite", sample_test_runs,
            traceability_links=sample_traceability_links,
        )
        assert "Traceability Audit" in report

    def test_report_empty_runs(self):
        report = generate_full_report("empty_suite", [])
        assert "METROLOGICAL CHARACTERIZATION REPORT" in report

    def test_report_with_specs(self, sample_test_runs):
        specs = [
            CapabilitySpec(test_name="test_login", usl=1.0, lsl=0.8),
        ]
        report = generate_full_report("test_suite", sample_test_runs, capability_specs=specs)
        assert "Capability Analysis" in report

    def test_report_with_mpe(self, sample_test_runs, sample_drift_observations):
        report = generate_full_report(
            "test_suite", sample_test_runs,
            drift_observations=sample_drift_observations,
            mpe=0.05,
        )
        assert "Drift Analysis" in report
