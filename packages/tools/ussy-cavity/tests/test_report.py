"""Tests for cavity.report module."""

from __future__ import annotations

import json

import numpy as np
import pytest

from cavity.report import CavityReport, generate_report
from cavity.topology import PipelineTopology


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_basic_report(self, simple_topology):
        report = generate_report(simple_topology)
        assert report.modes is not None
        assert report.impedance is not None
        assert report.damping is not None
        assert report.timestamp != ""

    def test_with_timeseries(self, simple_topology):
        wait = [1.0, 2.0, 3.0, 2.0, 1.0] * 20
        throughput = [0.0] * 100
        report = generate_report(
            simple_topology,
            wait_time_series=wait,
            throughput_series=throughput,
            fs=10.0,
        )
        assert report.standing_waves is not None
        assert report.beat_frequencies is not None

    def test_no_timeseries(self, simple_topology):
        report = generate_report(simple_topology)
        assert report.standing_waves is None
        assert report.beat_frequencies is None

    def test_pipeline_name(self, simple_topology):
        report = generate_report(simple_topology, pipeline_name="test_pipeline")
        assert report.pipeline_name == "test_pipeline"

    def test_custom_target_zeta(self, simple_topology):
        report = generate_report(simple_topology, target_zeta=0.8)
        assert report.damping is not None


# ---------------------------------------------------------------------------
# CavityReport serialization
# ---------------------------------------------------------------------------


class TestCavityReportSerialization:
    def test_to_dict(self, simple_topology):
        report = generate_report(simple_topology)
        d = report.to_dict()
        assert "timestamp" in d
        assert "modes" in d
        assert "impedance" in d
        assert "damping" in d

    def test_to_json(self, simple_topology):
        report = generate_report(simple_topology)
        j = report.to_json()
        data = json.loads(j)
        assert "timestamp" in data

    def test_to_text(self, simple_topology):
        report = generate_report(simple_topology)
        text = report.to_text()
        assert "CAVITY" in text
        assert "Resonance Modes" in text
        assert "Impedance Profile" in text
        assert "Damping Analysis" in text

    def test_to_text_with_waves(self, simple_topology):
        wait = list(np.sin(np.linspace(0, 20 * np.pi, 500)) * 5)
        report = generate_report(
            simple_topology,
            wait_time_series=wait,
            throughput_series=[0.0] * 500,
            fs=100.0,
        )
        text = report.to_text()
        assert "Standing Waves" in text or "No standing waves" in text
        assert "Beat Frequency" in text or "No beat frequencies" in text

    def test_json_roundtrip(self, simple_topology):
        report = generate_report(simple_topology)
        j = report.to_json()
        data = json.loads(j)
        # Verify it's valid JSON with expected structure
        assert isinstance(data["modes"], list)
        assert isinstance(data["impedance"], dict)
        assert isinstance(data["damping"], list)

    def test_modes_in_dict(self, simple_topology):
        report = generate_report(simple_topology)
        d = report.to_dict()
        for mode in d["modes"]:
            assert "frequency" in mode
            assert "damping_ratio" in mode
            assert "risk_level" in mode
            assert "q_factor" in mode

    def test_impedance_in_dict(self, simple_topology):
        report = generate_report(simple_topology)
        d = report.to_dict()
        imp = d["impedance"]
        assert "boundaries" in imp
        assert "mismatches" in imp
        for boundary in imp["boundaries"]:
            assert "upstream" in boundary
            assert "downstream" in boundary
            assert "reflection_coefficient" in boundary

    def test_damping_in_dict(self, simple_topology):
        report = generate_report(simple_topology)
        d = report.to_dict()
        for damp in d["damping"]:
            assert "stage" in damp
            assert "zeta" in damp
            assert "damping_class" in damp
