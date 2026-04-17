"""Tests for the capability index module."""

import math

import pytest

from calibre.capability import (
    capability_analysis,
    compute_cp,
    compute_cpk,
    compute_pp,
    compute_ppk,
    estimate_sigma_overall,
    estimate_sigma_within,
    format_capability,
)
from calibre.models import CapabilitySpec, TestResult, TestRun


class TestComputeCp:
    def test_basic(self):
        cp = compute_cp(usl=1.0, lsl=0.0, sigma_within=0.1)
        expected = 1.0 / (6.0 * 0.1)
        assert abs(cp - expected) < 1e-10

    def test_zero_sigma(self):
        cp = compute_cp(usl=1.0, lsl=0.0, sigma_within=0.0)
        assert cp == float("inf")

    def test_tight_spec(self):
        cp = compute_cp(usl=0.5, lsl=0.0, sigma_within=0.1)
        expected = 0.5 / 0.6
        assert abs(cp - expected) < 1e-10


class TestComputeCpk:
    def test_centered(self):
        cpk = compute_cpk(usl=1.0, lsl=0.0, mean=0.5, sigma_within=0.1)
        expected = min(0.5 / 0.3, 0.5 / 0.3)
        assert abs(cpk - expected) < 1e-10

    def test_off_center_high(self):
        cpk = compute_cpk(usl=1.0, lsl=0.0, mean=0.8, sigma_within=0.1)
        cpu = 0.2 / 0.3
        cpl = 0.8 / 0.3
        expected = min(cpu, cpl)
        assert abs(cpk - expected) < 1e-10

    def test_zero_sigma(self):
        cpk = compute_cpk(usl=1.0, lsl=0.0, mean=0.5, sigma_within=0.0)
        assert cpk == float("inf")


class TestComputePpPpk:
    def test_pp(self):
        pp = compute_pp(usl=1.0, lsl=0.0, sigma_overall=0.1)
        expected = 1.0 / 0.6
        assert abs(pp - expected) < 1e-10

    def test_ppk(self):
        ppk = compute_ppk(usl=1.0, lsl=0.0, mean=0.5, sigma_overall=0.1)
        expected = min(0.5 / 0.3, 0.5 / 0.3)
        assert abs(ppk - expected) < 1e-10


class TestEstimateSigma:
    def test_within_no_runs(self):
        assert estimate_sigma_within([]) == 0.0

    def test_overall_no_runs(self):
        assert estimate_sigma_overall([]) == 0.0

    def test_within_single_build(self):
        runs = [
            TestRun(test_name="t", module="m", suite="s", build_id="b1",
                    environment="e", result=TestResult.PASS),
            TestRun(test_name="t", module="m", suite="s", build_id="b1",
                    environment="e", result=TestResult.FAIL),
        ]
        sigma = estimate_sigma_within(runs)
        assert sigma > 0.0

    def test_overall_mixed(self):
        runs = [
            TestRun(test_name="t", module="m", suite="s", build_id="b1",
                    environment="e", result=TestResult.PASS),
            TestRun(test_name="t", module="m", suite="s", build_id="b1",
                    environment="e", result=TestResult.FAIL),
        ]
        sigma = estimate_sigma_overall(runs)
        assert sigma > 0.0


class TestCapabilityAnalysis:
    def test_no_runs(self):
        spec = CapabilitySpec(test_name="t1", usl=1.0, lsl=0.0)
        result = capability_analysis([], spec)
        assert result.test_name == "t1"
        assert not result.capable

    def test_capable_suite(self):
        """All pass → zero variation → inf Cp/Cpk."""
        runs = [
            TestRun(test_name="t1", module="m", suite="s", build_id=f"b{i}",
                    environment="e", result=TestResult.PASS)
            for i in range(20)
        ]
        spec = CapabilitySpec(test_name="t1", usl=1.0, lsl=0.8)
        result = capability_analysis(runs, spec)
        assert result.mean == 1.0

    def test_with_failures(self, sample_test_runs):
        spec = CapabilitySpec(test_name="auth", usl=1.0, lsl=0.8)
        result = capability_analysis(sample_test_runs, spec)
        assert result.cp is not None
        assert result.cpk is not None
        assert result.diagnosis != ""

    def test_low_cpk(self):
        """Many failures → low Cpk."""
        runs = []
        for i in range(10):
            for rep in range(3):
                result = TestResult.PASS if i % 3 != 0 else TestResult.FAIL
                runs.append(
                    TestRun(test_name="t1", module="m", suite="s", build_id=f"b{i}",
                            environment="e", result=result)
                )
        spec = CapabilitySpec(test_name="t1", usl=1.0, lsl=0.8)
        result = capability_analysis(runs, spec)
        # With ~33% failure rate, Cpk should be low (well below 1.33)
        assert result.cpk < 1.33 or not result.capable


class TestFormatCapability:
    def test_format(self):
        spec = CapabilitySpec(test_name="t1", usl=1.0, lsl=0.0)
        runs = [
            TestRun(test_name="t1", module="m", suite="s", build_id="b1",
                    environment="e", result=TestResult.PASS),
        ]
        result = capability_analysis(runs, spec)
        output = format_capability(result)
        assert "Capability Analysis" in output
        assert "Cp" in output
