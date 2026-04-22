"""Tests for the runner module."""

import pytest
import tempfile
from pathlib import Path

from ussy_syntrop.runner import run_probe, run_all_probes, probe_file, scan_directory, diff_probes
from ussy_syntrop.ir import ProbeResult, ScanResult, DiffResult
from ussy_syntrop.probes import PROBE_REGISTRY


SOURCE_ORDER_DEP = """
def main():
    result = []
    for item in [1, 2, 3]:
        result.append(item * 2)
    return result
"""

SOURCE_PURE = """
def main():
    return 2 + 3
"""


class TestRunProbe:
    """Tests for the run_probe function."""

    def test_run_known_probe(self):
        result = run_probe(SOURCE_PURE, "randomize-iteration", "main")
        assert isinstance(result, ProbeResult)
        assert result.probe_name == "randomize-iteration"

    def test_run_unknown_probe(self):
        with pytest.raises(ValueError, match="Unknown probe"):
            run_probe(SOURCE_PURE, "nonexistent-probe", "main")

    def test_run_each_probe(self):
        for name in PROBE_REGISTRY:
            result = run_probe(SOURCE_PURE, name, "main")
            assert isinstance(result, ProbeResult)


class TestRunAllProbes:
    """Tests for the run_all_probes function."""

    def test_run_all_probes(self):
        results = run_all_probes(SOURCE_PURE, "main")
        assert len(results) == len(PROBE_REGISTRY)

    def test_run_specific_probes(self):
        results = run_all_probes(SOURCE_PURE, "main", ["randomize-iteration"])
        assert len(results) == 1
        assert results[0].probe_name == "randomize-iteration"

    def test_results_are_probe_results(self):
        results = run_all_probes(SOURCE_PURE, "main")
        for result in results:
            assert isinstance(result, ProbeResult)


class TestProbeFile:
    """Tests for the probe_file function."""

    def test_probe_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SOURCE_PURE)
            f.flush()
            results = probe_file(f.name, ["randomize-iteration"])
            assert len(results) == 1
            assert isinstance(results[0], ProbeResult)


class TestScanDirectory:
    """Tests for the scan_directory function."""

    def test_scan_directory_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test Python file
            test_file = Path(tmpdir) / "test_code.py"
            test_file.write_text(SOURCE_ORDER_DEP)

            results = scan_directory(tmpdir, ["randomize-iteration"])
            assert len(results) >= 1
            assert isinstance(results[0], ScanResult)

    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = scan_directory(tmpdir)
            assert len(results) == 0

    def test_scan_results_have_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "code.py"
            test_file.write_text(SOURCE_ORDER_DEP)

            results = scan_directory(tmpdir)
            for result in results:
                assert result.path != ""
                assert isinstance(result.assumptions, list)


class TestDiffProbes:
    """Tests for the diff_probes function."""

    def test_diff_pure_code(self):
        result = diff_probes(SOURCE_PURE, ["randomize-iteration"], "main")
        assert isinstance(result, DiffResult)
        assert result.consistent  # Pure code shouldn't diverge

    def test_diff_all_probes(self):
        result = diff_probes(SOURCE_PURE)
        assert isinstance(result, DiffResult)
        assert len(result.modes_compared) == len(PROBE_REGISTRY)

    def test_diff_with_specific_probes(self):
        result = diff_probes(SOURCE_PURE, ["randomize-iteration", "alias-state"])
        assert len(result.modes_compared) == 2

    def test_diff_summary(self):
        result = diff_probes(SOURCE_PURE, ["randomize-iteration"])
        assert "divergence" in result.summary.lower() or "probe" in result.summary.lower()
