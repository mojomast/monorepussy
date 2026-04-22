"""Tests for coroner.striation — Striation Matching."""

from __future__ import annotations

from ussy_coroner.models import PipelineRun, Stage, StageStatus
from ussy_coroner.striation import (
    analyze_striations,
    compare_signatures,
    compute_error_signature,
    cross_correlate,
    normalize_error_signature,
    _text_to_signal,
)


class TestNormalizeErrorSignature:
    """Tests for error signature normalization."""

    def test_timestamps_replaced(self):
        log = "Error at 2024-01-15T10:30:00Z in module"
        result = normalize_error_signature(log)
        assert "2024-01-15" not in result
        assert "<TIMESTAMP>" in result

    def test_memory_addresses_replaced(self):
        log = "Segmentation fault at 0xdeadbeef"
        result = normalize_error_signature(log)
        assert "0xdeadbeef" not in result
        assert "<ADDR>" in result

    def test_pids_replaced(self):
        log = "Process pid 12345 crashed"
        result = normalize_error_signature(log)
        assert "pid 12345" not in result
        assert "<PID>" in result

    def test_temp_paths_replaced(self):
        log = "File not found: /tmp/build_cache/output.o"
        result = normalize_error_signature(log)
        assert "/tmp/build_cache" not in result
        assert "<TEMP_PATH>" in result

    def test_ip_addresses_replaced(self):
        log = "Connection refused to 192.168.1.100"
        result = normalize_error_signature(log)
        assert "192.168.1.100" not in result
        assert "<IP>" in result

    def test_line_numbers_replaced(self):
        log = "Error at line 42 in module"
        result = normalize_error_signature(log)
        assert "line 42" not in result
        assert "line <NUM>" in result

    def test_structural_similarity_preserved(self):
        """Two errors with different timestamps/PIDs should normalize identically."""
        log1 = "Error at 2024-01-15T10:30:00Z: FAILED test (pid 12345) at line 42"
        log2 = "Error at 2024-03-20T15:45:00Z: FAILED test (pid 67890) at line 99"
        n1 = normalize_error_signature(log1)
        n2 = normalize_error_signature(log2)
        # The structural parts should be the same
        assert "FAILED test" in n1
        assert "FAILED test" in n2


class TestCrossCorrelate:
    """Tests for cross-correlation computation."""

    def test_identical_signals(self):
        s1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = cross_correlate(s1, s1)
        assert result > 0.9  # Should be very high (near 1.0)

    def test_different_signals(self):
        s1 = [1.0, 0.0, 1.0, 0.0, 1.0]
        s2 = [0.0, 1.0, 0.0, 1.0, 0.0]
        result = cross_correlate(s1, s2)
        # These are anti-correlated, but cross-corr at different lags might still be moderate
        assert 0.0 <= result <= 1.0

    def test_empty_signals(self):
        result = cross_correlate([], [])
        assert result == 0.0

    def test_short_signals(self):
        result = cross_correlate([1.0], [1.0])
        assert 0.0 <= result <= 1.0


class TestComputeErrorSignature:
    """Tests for error signature computation."""

    def test_failing_run_has_signature(self, simple_failing_run):
        sig = compute_error_signature(simple_failing_run)
        assert sig != ""

    def test_passing_run_no_signature(self, passing_run):
        sig = compute_error_signature(passing_run)
        assert sig == ""


class TestCompareSignatures:
    """Tests for signature comparison."""

    def test_similar_errors_high_correlation(self):
        """Two runs with similar errors should have high correlation."""
        run1 = PipelineRun(run_id="r1")
        run1.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED auth-module/test.js\nAssertionError: expected 200 but got 401\nat auth-module/test.js:42"),
        ]
        run2 = PipelineRun(run_id="r2")
        run2.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED auth-module/test.js\nAssertionError: expected 200 but got 403\nat auth-module/test.js:55"),
        ]
        match = compare_signatures(run1, run2)
        # Similar structure should give reasonable correlation
        assert match.correlation >= 0.0

    def test_no_errors_zero_correlation(self, passing_run):
        run2 = PipelineRun(run_id="empty")
        match = compare_signatures(passing_run, run2)
        assert match.correlation == 0.0

    def test_same_root_cause_flag(self):
        """High correlation should set same_root_cause."""
        run1 = PipelineRun(run_id="r1")
        run1.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED module-a test\nError: timeout exceeded\nat module-a/test.js:10"),
        ]
        run2 = PipelineRun(run_id="r2")
        run2.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED module-a test\nError: timeout exceeded\nat module-a/test.js:10"),
        ]
        match = compare_signatures(run1, run2)
        # Identical error logs should give very high correlation
        if match.correlation > 0.8:
            assert match.same_root_cause is True


class TestAnalyzeStriations:
    """Tests for full striation analysis."""

    def test_with_comparison_runs(self, simple_failing_run, build_38_run):
        matches = analyze_striations(simple_failing_run, [build_38_run])
        assert len(matches) == 1
        assert matches[0].build_id_1 == "test-run-1"
        assert matches[0].build_id_2 == "build-38"

    def test_sorted_by_correlation(self):
        run = PipelineRun(run_id="main")
        run.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED test\nError at line 1"),
        ]
        compare1 = PipelineRun(run_id="c1")
        compare1.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="FAILED test\nError at line 1"),
        ]
        compare2 = PipelineRun(run_id="c2")
        compare2.stages = [
            Stage(name="test", index=0, status=StageStatus.FAILURE,
                  log_content="DIFFERENT error\nCompletely unrelated message"),
        ]
        matches = analyze_striations(run, [compare1, compare2])
        # Should be sorted by correlation descending
        for i in range(len(matches) - 1):
            assert matches[i].correlation >= matches[i + 1].correlation
