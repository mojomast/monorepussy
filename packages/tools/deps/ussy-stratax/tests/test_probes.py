"""Tests for probe generator and runner."""
import pytest
from ussy_stratax.models import Probe, ProbeResult
from ussy_stratax.probes.generator import ProbeGenerator
from ussy_stratax.probes.runner import ProbeRunner, SimulatedProbeRunner


class TestProbeGenerator:
    def setup_method(self):
        self.generator = ProbeGenerator()

    def test_generate_for_json_module(self):
        """Test generating probes for the stdlib json module."""
        probes = self.generator.generate_for_package("json")
        assert len(probes) > 0
        # Should find dumps, loads, etc.
        names = [p.name for p in probes]
        assert any("dumps" in n for n in names) or any("loads" in n for n in names)

    def test_generate_for_function(self):
        probes = self.generator.generate_for_function("json", "dumps")
        assert len(probes) > 0
        assert all(p.function == "dumps" for p in probes)

    def test_generate_for_nonexistent_package(self):
        probes = self.generator.generate_for_package("nonexistent_package_xyz_123")
        assert len(probes) == 0

    def test_generate_from_types(self):
        type_info = {
            "my_func": {"params": ["x", "y"], "returns": "int"},
            "other_func": {"params": []},
        }
        probes = self.generator.generate_from_types("mypkg", type_info)
        assert len(probes) >= 2
        names = [p.name for p in probes]
        assert any("my_func" in n for n in names)
        assert any("other_func" in n for n in names)

    def test_generated_probes_have_package(self):
        probes = self.generator.generate_for_package("json")
        for p in probes:
            assert p.package == "json"


class TestProbeRunner:
    def setup_method(self):
        self.runner = ProbeRunner()

    def test_run_simple_probe(self):
        probe = Probe(
            name="json.dumps exists",
            package="json",
            function="dumps",
            input_data={"obj": [1, 2, 3]},
            expected_output="[1, 2, 3]",
        )
        result = self.runner.run_probe(probe, "installed")
        assert result.probe_name == "json.dumps exists"
        # Should at least run without crashing
        assert result.execution_time_ms >= 0

    def test_run_nonexistent_package(self):
        probe = Probe(
            name="test",
            package="nonexistent_xyz_123",
            function="fn",
        )
        result = self.runner.run_probe(probe, "1.0.0")
        assert result.passed is False
        assert result.error is not None

    def test_run_probes_multiple(self):
        probes = [
            Probe(name="p1", package="json", function="dumps"),
            Probe(name="p2", package="json", function="loads"),
        ]
        results = self.runner.run_probes(probes, "installed")
        assert len(results) == 2

    def test_run_probes_for_version(self):
        probes = [Probe(name="p1", package="json", function="dumps")]
        vpr = self.runner.run_probes_for_version(probes, "json", "installed")
        assert vpr.package == "json"
        assert vpr.version == "installed"
        assert vpr.total_probes == 1


class TestSimulatedProbeRunner:
    def setup_method(self):
        self.runner = SimulatedProbeRunner()

    def test_no_data_fails(self):
        probe = Probe(name="test", package="pkg", function="fn")
        result = self.runner.run_probe(probe, "1.0.0")
        assert result.passed is False
        assert "No simulated data" in result.error

    def test_with_version_data(self):
        probe = Probe(
            name="test_probe",
            package="pkg",
            function="fn",
            expected_output=42,
        )
        self.runner.set_version_data("1.0.0", {"test_probe": 42})
        result = self.runner.run_probe(probe, "1.0.0")
        assert result.passed is True

    def test_with_wrong_output(self):
        probe = Probe(
            name="test_probe",
            package="pkg",
            function="fn",
            expected_output=42,
        )
        self.runner.set_version_data("1.0.0", {"test_probe": 99})
        result = self.runner.run_probe(probe, "1.0.0")
        assert result.passed is False

    def test_multiple_versions(self):
        probe = Probe(name="test", package="pkg", function="fn")
        self.runner.set_version_data("1.0.0", {"test": "hello"})
        self.runner.set_version_data("2.0.0", {"test": "world"})
        
        r1 = self.runner.run_probe(probe, "1.0.0")
        r2 = self.runner.run_probe(probe, "2.0.0")
        # Both should succeed (no expected_output = pass if output exists)
        assert r1.actual_output == "hello"
        assert r2.actual_output == "world"
