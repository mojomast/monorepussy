"""Tests for cavity.damping module."""

from __future__ import annotations

import pytest

from ussy_cavity.damping import (
    DampingClass,
    DampingResult,
    analyze_stage_damping,
    classify_damping_class,
    compute_damping_ratio,
    format_damping_results,
    recommend_adjustment,
)


# ---------------------------------------------------------------------------
# compute_damping_ratio
# ---------------------------------------------------------------------------


class TestComputeDampingRatio:
    def test_critical_damping(self):
        # ζ = c / (2√(km)) = 2 / (2√(1×1)) = 1.0
        zeta = compute_damping_ratio(backoff_rate=2.0, contention_strength=1.0, work_inertia=1.0)
        assert abs(zeta - 1.0) < 1e-10

    def test_undamped(self):
        zeta = compute_damping_ratio(backoff_rate=0.0, contention_strength=1.0, work_inertia=1.0)
        assert zeta == 0.0

    def test_overdamped(self):
        # ζ = 10 / (2√(1×1)) = 5.0
        zeta = compute_damping_ratio(backoff_rate=10.0, contention_strength=1.0, work_inertia=1.0)
        assert zeta == 5.0

    def test_underdamped(self):
        # ζ = 0.1 / (2√(1×1)) = 0.05
        zeta = compute_damping_ratio(backoff_rate=0.1, contention_strength=1.0, work_inertia=1.0)
        assert abs(zeta - 0.05) < 1e-10

    def test_zero_km_product(self):
        zeta = compute_damping_ratio(backoff_rate=1.0, contention_strength=0.0, work_inertia=1.0)
        assert zeta == 0.0

    def test_large_values(self):
        zeta = compute_damping_ratio(backoff_rate=1000.0, contention_strength=100.0, work_inertia=100.0)
        expected = 1000.0 / (2.0 * (100.0 * 100.0) ** 0.5)
        assert abs(zeta - expected) < 1e-6


# ---------------------------------------------------------------------------
# classify_damping_class
# ---------------------------------------------------------------------------


class TestClassifyDampingClass:
    def test_undamped(self):
        assert classify_damping_class(0.0) == DampingClass.UNDAMPED
        assert classify_damping_class(0.04) == DampingClass.UNDAMPED

    def test_underdamped(self):
        assert classify_damping_class(0.1) == DampingClass.UNDERDAMPED
        assert classify_damping_class(0.5) == DampingClass.UNDERDAMPED
        assert classify_damping_class(0.9) == DampingClass.UNDERDAMPED

    def test_critical(self):
        assert classify_damping_class(0.96) == DampingClass.CRITICALLY_DAMPED
        assert classify_damping_class(1.0) == DampingClass.CRITICALLY_DAMPED
        assert classify_damping_class(1.05) == DampingClass.CRITICALLY_DAMPED

    def test_overdamped(self):
        assert classify_damping_class(1.2) == DampingClass.OVERDAMPED
        assert classify_damping_class(10.0) == DampingClass.OVERDAMPED


# ---------------------------------------------------------------------------
# recommend_adjustment
# ---------------------------------------------------------------------------


class TestRecommendAdjustment:
    def test_optimal(self):
        rec = recommend_adjustment(1.0, target=1.0)
        assert "no adjustment" in rec.lower() or "optimal" in rec.lower()

    def test_too_low(self):
        rec = recommend_adjustment(0.3, target=1.0)
        assert "too low" in rec.lower() or "increase" in rec.lower()

    def test_very_low(self):
        rec = recommend_adjustment(0.01, target=1.0)
        assert "too low" in rec.lower()

    def test_too_high(self):
        rec = recommend_adjustment(3.0, target=1.0)
        assert "too high" in rec.lower() or "decrease" in rec.lower()

    def test_very_high(self):
        rec = recommend_adjustment(5.0, target=1.0)
        assert "too high" in rec.lower()

    def test_near_target(self):
        rec = recommend_adjustment(1.05, target=1.0)
        assert "no adjustment" in rec.lower() or "near" in rec.lower()


# ---------------------------------------------------------------------------
# analyze_stage_damping
# ---------------------------------------------------------------------------


class TestAnalyzeStageDamping:
    def test_simple_topology(self, simple_topology):
        results = analyze_stage_damping(simple_topology)
        assert len(results) == 3  # 3 stages
        for r in results:
            assert isinstance(r, DampingResult)
            assert r.zeta >= 0.0
            assert isinstance(r.damping_class, DampingClass)

    def test_complex_topology(self, complex_topology):
        results = analyze_stage_damping(complex_topology)
        assert len(results) == 7  # 7 stages

    def test_has_recommendations(self, simple_topology):
        results = analyze_stage_damping(simple_topology)
        for r in results:
            assert isinstance(r.recommendation, str)

    def test_custom_target(self, simple_topology):
        results = analyze_stage_damping(simple_topology, target_zeta=0.7)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# DampingResult
# ---------------------------------------------------------------------------


class TestDampingResult:
    def test_summary(self):
        r = DampingResult(
            stage_name="test", zeta=0.5,
            damping_class=DampingClass.UNDERDAMPED,
            backoff_rate=1.0, contention_strength=1.0, work_inertia=1.0,
        )
        s = r.summary()
        assert "test" in s
        assert "UNDERDAMPED" in s


# ---------------------------------------------------------------------------
# format_damping_results
# ---------------------------------------------------------------------------


class TestFormatDampingResults:
    def test_empty(self):
        s = format_damping_results([])
        assert "No stages" in s

    def test_with_results(self, simple_topology):
        results = analyze_stage_damping(simple_topology)
        s = format_damping_results(results)
        assert "Damping Analysis" in s
