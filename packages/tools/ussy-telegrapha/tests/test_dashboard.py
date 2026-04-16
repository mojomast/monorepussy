"""Tests for the dashboard module."""

import json
import pytest
from pathlib import Path

from telegrapha.models import Hop, Route, PipelineTopology
from telegrapha.dashboard import (
    generate_dashboard,
    format_dashboard_report,
)


class TestGenerateDashboard:
    """Tests for dashboard generation."""

    def test_basic_dashboard(self):
        topology = PipelineTopology(
            name="test-pipeline",
            routes=[
                Route(
                    name="route-1",
                    hops=[
                        Hop(name="h1", degradation=0.01, reliability=0.999),
                        Hop(name="h2", degradation=0.02, reliability=0.998),
                    ],
                ),
            ],
        )
        dashboard = generate_dashboard(topology)
        assert dashboard["topology"] == "test-pipeline"
        assert len(dashboard["routes"]) == 1
        assert dashboard["capacity"] is not None
        assert dashboard["hamming"] is not None

    def test_dashboard_with_dlq(self, sample_dlq_json):
        topology = PipelineTopology(
            name="test-pipeline",
            routes=[
                Route(name="r1", hops=[Hop(name="h1", degradation=0.01)]),
            ],
        )
        dashboard = generate_dashboard(
            topology,
            dlq_path=str(sample_dlq_json),
            dlq_accumulation_rate=47.0,
            dlq_resolution_rate=12.0,
        )
        assert dashboard["dlo"] is not None

    def test_dashboard_without_dlq(self):
        topology = PipelineTopology(
            name="test",
            routes=[Route(name="r1", hops=[Hop(name="h1")])],
        )
        dashboard = generate_dashboard(topology)
        assert dashboard["dlo"] is None

    def test_dashboard_json_serializable(self):
        topology = PipelineTopology(
            name="test",
            routes=[
                Route(name="r1", hops=[
                    Hop(name="h1", degradation=0.01, reliability=0.999),
                ]),
            ],
        )
        dashboard = generate_dashboard(topology)
        json_str = json.dumps(dashboard)
        assert json_str


class TestFormatDashboardReport:
    """Tests for dashboard report formatting."""

    def test_report_format(self):
        topology = PipelineTopology(
            name="test-pipeline",
            routes=[
                Route(
                    name="route-1",
                    hops=[
                        Hop(name="h1", degradation=0.01, reliability=0.999),
                    ],
                ),
            ],
        )
        dashboard = generate_dashboard(topology)
        report = format_dashboard_report(dashboard)
        assert "TELEGRAPHA DASHBOARD" in report
        assert "test-pipeline" in report

    def test_report_with_dlq(self, sample_dlq_json):
        topology = PipelineTopology(
            name="test",
            routes=[Route(name="r1", hops=[Hop(name="h1")])],
        )
        dashboard = generate_dashboard(
            topology,
            dlq_path=str(sample_dlq_json),
            dlq_accumulation_rate=47.0,
            dlq_resolution_rate=12.0,
        )
        report = format_dashboard_report(dashboard)
        assert "Dead Letter Office" in report
