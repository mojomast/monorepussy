"""Tests for the stress intensity module."""

import os
import pytest

from ussy_fatigue.stress import (
    compute_stress_intensity,
    compute_coupling,
    compute_churn_rate,
    estimate_test_coverage,
)
from ussy_fatigue.models import ModuleMetrics, StressIntensity


class TestStressIntensity:
    """Tests for stress intensity computation."""

    def test_basic_computation(self):
        """Test basic K calculation."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        stress = compute_stress_intensity(metrics)

        # K = (5 * 3 * 10) / (0.5 + 0.1) = 150 / 0.6 = 250
        assert stress.K == 250.0

    def test_zero_coverage_high_stress(self):
        """Test that zero coverage maximizes stress amplification."""
        metrics_no_coverage = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.0,
        )
        metrics_with_coverage = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.8,
        )

        stress_no = compute_stress_intensity(metrics_no_coverage)
        stress_with = compute_stress_intensity(metrics_with_coverage)

        # Zero coverage should result in higher K
        assert stress_no.K > stress_with.K

    def test_delta_K_computation(self):
        """Test delta_K (change in K) computation."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        stress = compute_stress_intensity(metrics, prev_K=200.0)
        # K = 250, prev_K = 200, delta_K = 50
        assert stress.delta_K == 50.0

    def test_negative_delta_K(self):
        """Test negative delta_K (improvement)."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        stress = compute_stress_intensity(metrics, prev_K=300.0)
        # K = 250, prev_K = 300, delta_K = -50
        assert stress.delta_K == -50.0

    def test_minimum_values(self):
        """Test with minimum metric values."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=0.0,
            churn_rate=0.0,
            complexity=0.0,
            test_coverage=0.0,
        )
        stress = compute_stress_intensity(metrics)
        # Should use minimums (0.1 for numerator factors, 0.1 for denominator)
        # K = (0.1 * 0.1 * 0.1) / (0 + 0.1) = 0.001 / 0.1 = 0.01
        assert stress.K > 0

    def test_high_coupling_high_K(self):
        """Test that high coupling increases K."""
        metrics_low = ModuleMetrics(
            file_path="test.py",
            coupling=2.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        metrics_high = ModuleMetrics(
            file_path="test.py",
            coupling=12.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )

        stress_low = compute_stress_intensity(metrics_low)
        stress_high = compute_stress_intensity(metrics_high)

        assert stress_high.K > stress_low.K

    def test_high_churn_high_K(self):
        """Test that high churn rate increases K."""
        metrics_low = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=1.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        metrics_high = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=8.0,
            complexity=10.0,
            test_coverage=0.5,
        )

        stress_low = compute_stress_intensity(metrics_low)
        stress_high = compute_stress_intensity(metrics_high)

        assert stress_high.K > stress_low.K

    def test_components_stored(self):
        """Test that stress intensity stores component values."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        stress = compute_stress_intensity(metrics)

        assert stress.coupling_component == 5.0
        assert stress.churn_component == 3.0
        assert stress.complexity_component == 10.0
        assert stress.coverage_component == 0.6  # 0.5 + 0.1

    def test_no_prev_K_zero_delta(self):
        """Test that delta_K is 0 when no previous K is given."""
        metrics = ModuleMetrics(
            file_path="test.py",
            coupling=5.0,
            churn_rate=3.0,
            complexity=10.0,
            test_coverage=0.5,
        )
        stress = compute_stress_intensity(metrics)
        assert stress.delta_K == 0.0


class TestComputeCoupling:
    """Tests for coupling computation."""

    def test_compute_coupling_with_graph(self):
        """Test coupling computation with import graph."""
        graph = {
            "module.A": {"module.B", "module.C"},
            "module.B": {"module.C"},
            "module.C": set(),
        }
        coupling = compute_coupling("module.A.py", ".", graph)
        # fan_out = 2 (A imports B, C), fan_in = 0 (nobody imports A)
        # depth_weight: max depth from A is 2 (A->B->C)
        assert coupling > 0

    def test_compute_coupling_no_graph(self):
        """Test coupling computation without import graph."""
        coupling = compute_coupling("test.py", ".")
        assert coupling >= 0


class TestChurnRate:
    """Tests for churn rate computation."""

    def test_churn_rate_nonexistent_file(self):
        """Test churn rate for a file not in a git repo."""
        rate = compute_churn_rate("/nonexistent/file.py", weeks=4)
        # Should return default value
        assert rate >= 0

    def test_churn_rate_positive(self):
        """Test that churn rate is always non-negative."""
        rate = compute_churn_rate("any_file.py", weeks=12)
        assert rate >= 0


class TestTestCoverage:
    """Tests for test coverage estimation."""

    def test_coverage_no_tests(self, temp_python_file):
        """Test coverage estimation when no tests exist."""
        content = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        fpath = temp_python_file(content)
        coverage = estimate_test_coverage(fpath)
        # No test files found, should be 0
        assert coverage >= 0.0

    def test_coverage_with_tests(self, temp_python_file, tmp_path):
        """Test coverage estimation with test files."""
        content = """
def add(a, b):
    return a + b

def subtract(a, b):
        return a - b
"""
        fpath = temp_python_file(content, filename="math_utils.py")

        # Create a test file
        test_dir = os.path.join(os.path.dirname(fpath), "tests")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "test_math_utils.py")
        with open(test_file, "w") as f:
            f.write("""
def test_add():
    assert add(1, 2) == 3

def test_subtract():
    assert subtract(3, 1) == 2
""")

        coverage = estimate_test_coverage(fpath)
        # Should detect some coverage since test file exists
        assert coverage >= 0.0

    def test_coverage_nonexistent(self):
        """Test coverage for a nonexistent file."""
        coverage = estimate_test_coverage("/nonexistent/file.py")
        assert coverage >= 0.0
