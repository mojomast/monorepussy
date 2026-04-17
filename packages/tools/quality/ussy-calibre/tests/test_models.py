"""Tests for the data models."""

from datetime import datetime, timezone

from calibre.models import (
    CapabilityResult,
    CapabilitySpec,
    DriftObservation,
    DriftResult,
    FlakinessClassification,
    RRCategory,
    RRObservation,
    RRSummary,
    TestResult,
    TestRun,
    TraceabilityLink,
    TraceabilityResult,
    UncertaintyBudget,
    UncertaintySource,
    UncertaintyType,
)


class TestTestResult:
    __test__ = False

    def test_pass_value(self):
        assert TestResult.PASS.value == "pass"

    def test_fail_value(self):
        assert TestResult.FAIL.value == "fail"


class TestTestRun:
    __test__ = False

    def test_passed_property(self):
        run = TestRun(
            test_name="t1", module="m1", suite="s1",
            build_id="b1", environment="e1", result=TestResult.PASS,
        )
        assert run.passed is True

    def test_failed_property(self):
        run = TestRun(
            test_name="t1", module="m1", suite="s1",
            build_id="b1", environment="e1", result=TestResult.FAIL,
        )
        assert run.passed is False

    def test_numeric_result_pass(self):
        run = TestRun(
            test_name="t1", module="m1", suite="s1",
            build_id="b1", environment="e1", result=TestResult.PASS,
        )
        assert run.numeric_result == 1.0

    def test_numeric_result_fail(self):
        run = TestRun(
            test_name="t1", module="m1", suite="s1",
            build_id="b1", environment="e1", result=TestResult.FAIL,
        )
        assert run.numeric_result == 0.0

    def test_default_timestamp(self):
        run = TestRun(
            test_name="t1", module="m1", suite="s1",
            build_id="b1", environment="e1", result=TestResult.PASS,
        )
        assert run.timestamp is not None
        assert run.timestamp.tzinfo is not None


class TestUncertaintySource:
    __test__ = False

    def test_contribution(self):
        s = UncertaintySource(
            name="test", uncertainty_value=0.1, sensitivity_coefficient=2.0,
        )
        assert s.contribution == (2.0 * 0.1) ** 2  # 0.04

    def test_contribution_zero(self):
        s = UncertaintySource(
            name="test", uncertainty_value=0.0, sensitivity_coefficient=1.0,
        )
        assert s.contribution == 0.0


class TestUncertaintyBudget:
    __test__ = False

    def test_confidence_level_k2(self):
        b = UncertaintyBudget(measurand="test", coverage_factor=2.0)
        assert b.confidence_level == 0.9545

    def test_confidence_level_k1(self):
        b = UncertaintyBudget(measurand="test", coverage_factor=1.0)
        assert b.confidence_level == 0.6827


class TestRRCategory:
    __test__ = False

    def test_values(self):
        assert RRCategory.ACCEPTABLE.value == "acceptable"
        assert RRCategory.CONDITIONAL.value == "conditional"
        assert RRCategory.UNACCEPTABLE.value == "unacceptable"
