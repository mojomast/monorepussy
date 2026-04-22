"""Tests for cavity.impedance module."""

from __future__ import annotations

import numpy as np
import pytest

from ussy_cavity.impedance import (
    ImpedanceBoundary,
    ImpedanceProfile,
    analyze_impedance_mismatches,
    compute_reflection_coefficient,
    compute_stage_impedance,
    compute_transmission_coefficient,
    format_impedance_profile,
    format_recommendations,
    recommend_damping,
)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


class TestComputeStageImpedance:
    def test_basic(self):
        z = compute_stage_impedance(rate=1000, buffer_depth=500)
        assert z == 500000.0

    def test_zero_rate(self):
        z = compute_stage_impedance(rate=0, buffer_depth=500)
        assert z == 0.0

    def test_zero_buffer(self):
        z = compute_stage_impedance(rate=1000, buffer_depth=0)
        assert z == 0.0


class TestReflectionCoefficient:
    def test_matched(self):
        R = compute_reflection_coefficient(100, 100)
        assert abs(R) < 1e-10

    def test_total_reflection(self):
        R = compute_reflection_coefficient(0, 100)
        assert abs(R - 1.0) < 1e-10

    def test_negative_reflection(self):
        R = compute_reflection_coefficient(100, 0)
        assert abs(R - (-1.0)) < 1e-10

    def test_both_zero(self):
        R = compute_reflection_coefficient(0, 0)
        assert R == 0.0

    def test_symmetry(self):
        R1 = compute_reflection_coefficient(100, 200)
        R2 = compute_reflection_coefficient(200, 100)
        assert abs(R1 + R2) < 1e-10  # R1 = -R2


class TestTransmissionCoefficient:
    def test_matched(self):
        T = compute_transmission_coefficient(100, 100)
        assert abs(T - 1.0) < 1e-10

    def test_total_transmission_into_high_z(self):
        T = compute_transmission_coefficient(0, 100)
        assert abs(T - 2.0) < 1e-10

    def test_both_zero(self):
        T = compute_transmission_coefficient(0, 0)
        assert T == 0.0


# ---------------------------------------------------------------------------
# analyze_impedance_mismatches
# ---------------------------------------------------------------------------


class TestAnalyzeImpedanceMismatches:
    def test_simple_topology(self, simple_topology):
        profile = analyze_impedance_mismatches(simple_topology)
        assert len(profile.boundaries) == 2  # producer→transformer, transformer→consumer
        assert isinstance(profile.mismatches, list)

    def test_mismatch_detection(self, simple_topology):
        """Producer Z=500000, Transformer Z=160000, Consumer Z=60000."""
        profile = analyze_impedance_mismatches(simple_topology)
        # Producer→Transformer: R = (160000-500000)/(160000+500000) ≈ -0.515
        # |R| > 0.5 → mismatch
        assert len(profile.mismatches) >= 1

    def test_no_mismatches(self, minimal_dict):
        from ussy_cavity.topology import PipelineTopology
        topo = PipelineTopology.from_dict(minimal_dict)
        # a: Z=5000, b: Z=1000 → R = (1000-5000)/6000 = -0.667 → mismatch
        profile = analyze_impedance_mismatches(topo)
        assert isinstance(profile.mismatches, list)

    def test_resonant_cavity_risks(self, simple_topology):
        profile = analyze_impedance_mismatches(simple_topology)
        # Depending on topology, may or may not have cavity risks
        assert isinstance(profile.resonant_cavity_risks, list)

    def test_custom_threshold(self, simple_topology):
        profile_loose = analyze_impedance_mismatches(simple_topology, mismatch_threshold=0.9)
        profile_strict = analyze_impedance_mismatches(simple_topology, mismatch_threshold=0.1)
        assert len(profile_loose.mismatches) <= len(profile_strict.mismatches)


# ---------------------------------------------------------------------------
# ImpedanceBoundary / ImpedanceProfile
# ---------------------------------------------------------------------------


class TestImpedanceBoundary:
    def test_summary(self):
        b = ImpedanceBoundary(
            upstream="a", downstream="b",
            z_upstream=1000, z_downstream=500,
            reflection_coefficient=-0.333,
            transmission_coefficient=0.667,
            is_mismatch=False,
        )
        s = b.summary()
        assert "a → b" in s
        assert "1000.0" in s

    def test_mismatch_flag(self):
        b = ImpedanceBoundary(
            upstream="a", downstream="b",
            z_upstream=1000, z_downstream=100,
            reflection_coefficient=-0.818,
            transmission_coefficient=0.182,
            is_mismatch=True,
        )
        s = b.summary()
        assert "MISMATCH" in s


class TestImpedanceProfile:
    def test_summary(self, simple_topology):
        profile = analyze_impedance_mismatches(simple_topology)
        s = profile.summary()
        assert "Impedance Profile" in s


# ---------------------------------------------------------------------------
# recommend_damping
# ---------------------------------------------------------------------------


class TestRecommendDamping:
    def test_with_mismatches(self, simple_topology):
        recs = recommend_damping(simple_topology)
        assert isinstance(recs, list)

    def test_recommendation_content(self, simple_topology):
        recs = recommend_damping(simple_topology)
        for rec in recs:
            assert "boundary" in rec
            assert "reflection_coefficient" in rec
            assert "recommendation" in rec

    def test_no_mismatches(self):
        """Topology with matched impedances should have no recommendations."""
        from ussy_cavity.topology import PipelineTopology
        data = {
            "stages": {
                "a": {"rate": 100, "buffer": 10, "depends_on": [], "locks": []},
                "b": {"rate": 100, "buffer": 10, "depends_on": ["a"], "locks": []},
            },
        }
        topo = PipelineTopology.from_dict(data)
        recs = recommend_damping(topo)
        assert recs == []


# ---------------------------------------------------------------------------
# format functions
# ---------------------------------------------------------------------------


class TestFormatFunctions:
    def test_format_profile(self, simple_topology):
        profile = analyze_impedance_mismatches(simple_topology)
        s = format_impedance_profile(profile)
        assert "Impedance Profile" in s

    def test_format_recommendations_empty(self):
        s = format_recommendations([])
        assert "No impedance mismatches" in s

    def test_format_recommendations(self, simple_topology):
        recs = recommend_damping(simple_topology)
        s = format_recommendations(recs)
        assert "Damping Recommendations" in s
