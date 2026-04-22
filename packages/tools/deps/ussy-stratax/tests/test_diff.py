"""Tests for version diff comparison."""
import pytest
from ussy_stratax.models import ProbeResult, VersionProbeResult
from ussy_stratax.diff import VersionDiffer


def make_version_result(version, passes):
    """Create a VersionProbeResult with given pass/fail pattern."""
    results = [
        ProbeResult(f"probe_{i}", "pkg", version, passed=p)
        for i, p in enumerate(passes)
    ]
    return VersionProbeResult(package="pkg", version=version, results=results)


class TestVersionDiffer:
    def setup_method(self):
        self.differ = VersionDiffer()

    def test_identical_versions(self):
        a = make_version_result("1.0.0", [True, True, True])
        b = make_version_result("2.0.0", [True, True, True])
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert not diff.has_quakes
        assert diff.unchanged_count == 3
        assert len(diff.behavioral_quakes) == 0

    def test_behavioral_quake(self):
        a = make_version_result("1.0.0", [True, True, True])
        b = make_version_result("2.0.0", [True, False, True])
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert diff.has_quakes
        assert len(diff.behavioral_quakes) == 1
        assert diff.behavioral_quakes[0]["probe"] == "probe_1"

    def test_multiple_quakes(self):
        a = make_version_result("1.0.0", [True, False, True])
        b = make_version_result("2.0.0", [False, True, False])
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert diff.has_quakes
        assert len(diff.behavioral_quakes) == 3

    def test_new_behaviors(self):
        a = make_version_result("1.0.0", [True, True])
        b = make_version_result("2.0.0", [True, True, True])  # Extra probe
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert len(diff.new_behaviors) == 1
        assert "probe_2" in diff.new_behaviors

    def test_removed_behaviors(self):
        a = make_version_result("1.0.0", [True, True, True])
        b = make_version_result("2.0.0", [True, True])  # Missing probe
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert len(diff.removed_behaviors) == 1
        assert "probe_2" in diff.removed_behaviors

    def test_diff_from_history(self):
        history = [
            make_version_result("1.0.0", [True, True]),
            make_version_result("1.1.0", [True, False]),
            make_version_result("2.0.0", [False, False]),
        ]
        diff = self.differ.diff_from_history("pkg", "1.0.0", "2.0.0", history)
        assert diff.has_quakes
        assert len(diff.behavioral_quakes) == 2

    def test_diff_from_history_missing_version(self):
        history = [
            make_version_result("1.0.0", [True, True]),
        ]
        with pytest.raises(ValueError, match="not found"):
            self.differ.diff_from_history("pkg", "1.0.0", "9.9.9", history)

    def test_empty_results(self):
        a = VersionProbeResult(package="pkg", version="1.0.0", results=[])
        b = VersionProbeResult(package="pkg", version="2.0.0", results=[])
        diff = self.differ.diff("pkg", "1.0.0", "2.0.0", a, b)
        assert not diff.has_quakes
        assert diff.unchanged_count == 0
