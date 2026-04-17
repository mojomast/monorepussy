"""Tests for core data models."""
import pytest
from strata.models import (
    Probe,
    ProbeResult,
    VersionProbeResult,
    BedrockReport,
    SeismicReport,
    FaultLine,
    ErosionReport,
    StratigraphicColumn,
    DiffResult,
    ScanResult,
)


class TestProbe:
    def test_create_probe(self):
        p = Probe(name="test_probe", package="numpy", function="array")
        assert p.name == "test_probe"
        assert p.package == "numpy"
        assert p.function == "array"
        assert p.input_data is None
        assert p.expected_output is None

    def test_probe_to_dict(self):
        p = Probe(name="test", package="pkg", function="func", returns_type="int")
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["package"] == "pkg"
        assert d["returns_type"] == "int"

    def test_probe_with_all_fields(self):
        p = Probe(
            name="full_probe",
            package="pkg",
            function="fn",
            input_data=[1, 2, 3],
            expected_output=6,
            output_has_keys=["a", "b"],
            target_mutated=False,
            raises="ValueError",
            returns_type="int",
            custom_assertion="custom check",
        )
        assert p.input_data == [1, 2, 3]
        assert p.expected_output == 6
        assert p.output_has_keys == ["a", "b"]
        assert p.raises == "ValueError"


class TestProbeResult:
    def test_create_result(self):
        r = ProbeResult(
            probe_name="test", package="pkg", version="1.0.0", passed=True
        )
        assert r.passed is True
        assert r.actual_output is None
        assert r.execution_time_ms == 0.0

    def test_failed_result(self):
        r = ProbeResult(
            probe_name="test",
            package="pkg",
            version="1.0.0",
            passed=False,
            error="ImportError",
        )
        assert r.passed is False
        assert r.error == "ImportError"


class TestVersionProbeResult:
    def test_empty_results(self):
        vpr = VersionProbeResult(package="pkg", version="1.0.0")
        assert vpr.total_probes == 0
        assert vpr.passed_count == 0
        assert vpr.pass_rate == 0.0

    def test_with_results(self):
        vpr = VersionProbeResult(
            package="pkg",
            version="1.0.0",
            results=[
                ProbeResult("p1", "pkg", "1.0.0", True),
                ProbeResult("p2", "pkg", "1.0.0", True),
                ProbeResult("p3", "pkg", "1.0.0", False),
            ],
        )
        assert vpr.total_probes == 3
        assert vpr.passed_count == 2
        assert vpr.pass_rate == pytest.approx(2 / 3)

    def test_all_passed(self):
        vpr = VersionProbeResult(
            package="pkg",
            version="1.0.0",
            results=[
                ProbeResult("p1", "pkg", "1.0.0", True),
                ProbeResult("p2", "pkg", "1.0.0", True),
            ],
        )
        assert vpr.pass_rate == 1.0


class TestBedrockReport:
    def test_bedrock_tier(self):
        r = BedrockReport(
            package="pkg", function="fn", bedrock_score=95.0,
            versions_stable=10, versions_total=10, years_stable=3.0,
        )
        assert r.stability_tier == "bedrock"

    def test_stable_tier(self):
        r = BedrockReport(
            package="pkg", function="fn", bedrock_score=70.0,
            versions_stable=7, versions_total=10, years_stable=1.0,
        )
        assert r.stability_tier == "stable"

    def test_hazard_tier(self):
        r = BedrockReport(
            package="pkg", function="fn", bedrock_score=50.0,
            versions_stable=5, versions_total=10, years_stable=0.5,
        )
        assert r.stability_tier == "hazard"

    def test_quicksand_tier(self):
        r = BedrockReport(
            package="pkg", function="fn", bedrock_score=20.0,
            versions_stable=2, versions_total=10, years_stable=0.0,
        )
        assert r.stability_tier == "quicksand"

    def test_deprecated_tier(self):
        r = BedrockReport(
            package="pkg", function="fn", bedrock_score=5.0,
            versions_stable=0, versions_total=10, years_stable=0.0,
        )
        assert r.stability_tier == "deprecated"

    def test_boundary_values(self):
        # Exactly 90 should be bedrock
        r = BedrockReport(package="pkg", function="fn", bedrock_score=90.0,
                          versions_stable=9, versions_total=10, years_stable=1.0)
        assert r.stability_tier == "bedrock"

        # Exactly 65 should be stable
        r = BedrockReport(package="pkg", function="fn", bedrock_score=65.0,
                          versions_stable=6, versions_total=10, years_stable=1.0)
        assert r.stability_tier == "stable"

        # Exactly 35 should be hazard
        r = BedrockReport(package="pkg", function="fn", bedrock_score=35.0,
                          versions_stable=3, versions_total=10, years_stable=0.5)
        assert r.stability_tier == "hazard"

        # Exactly 15 should be quicksand
        r = BedrockReport(package="pkg", function="fn", bedrock_score=15.0,
                          versions_stable=1, versions_total=10, years_stable=0.0)
        assert r.stability_tier == "quicksand"


class TestSeismicReport:
    def test_dormant(self):
        r = SeismicReport(
            package="pkg", function="fn", quakes_per_version=0.01,
            total_quakes=1, versions_scanned=20, recent_quakes=0,
        )
        assert r.hazard_level == "dormant"

    def test_minor(self):
        r = SeismicReport(
            package="pkg", function="fn", quakes_per_version=0.10,
            total_quakes=2, versions_scanned=20, recent_quakes=1,
        )
        assert r.hazard_level == "minor"

    def test_moderate(self):
        r = SeismicReport(
            package="pkg", function="fn", quakes_per_version=0.25,
            total_quakes=5, versions_scanned=20, recent_quakes=3,
        )
        assert r.hazard_level == "moderate"

    def test_major(self):
        r = SeismicReport(
            package="pkg", function="fn", quakes_per_version=0.45,
            total_quakes=9, versions_scanned=20, recent_quakes=4,
        )
        assert r.hazard_level == "major"

    def test_catastrophic(self):
        r = SeismicReport(
            package="pkg", function="fn", quakes_per_version=0.80,
            total_quakes=16, versions_scanned=20, recent_quakes=5,
        )
        assert r.hazard_level == "catastrophic"


class TestFaultLine:
    def test_create_fault_line(self):
        fl = FaultLine(
            package="pkg",
            bedrock_function="stable_fn",
            unstable_function="unstable_fn",
            bedrock_score=95.0,
            unstable_score=10.0,
            description="Test fault line",
        )
        assert fl.bedrock_score > fl.unstable_score
        assert fl.bedrock_function == "stable_fn"


class TestErosionReport:
    def test_eroding(self):
        r = ErosionReport(
            package="pkg", function="fn", erosion_rate=-0.05,
            initial_pass_rate=1.0, current_pass_rate=0.7,
            versions_declining=5, is_eroding=True,
        )
        assert r.is_eroding is True
        assert r.erosion_rate < 0

    def test_not_eroding(self):
        r = ErosionReport(
            package="pkg", function="fn", erosion_rate=0.01,
            initial_pass_rate=0.9, current_pass_rate=0.95,
            versions_declining=0, is_eroding=False,
        )
        assert r.is_eroding is False


class TestStratigraphicColumn:
    def test_empty_column(self):
        col = StratigraphicColumn(package="pkg")
        assert col.total_functions == 0
        assert col.bedrock_reports == []
        assert col.fault_lines == []

    def test_column_with_data(self):
        col = StratigraphicColumn(
            package="pkg",
            bedrock_reports=[
                BedrockReport("pkg", "fn1", 90.0, 9, 10, 2.0),
                BedrockReport("pkg", "fn2", 30.0, 3, 10, 0.5),
            ],
            fault_lines=[
                FaultLine("pkg", "fn1", "fn2", 90.0, 30.0),
            ],
        )
        assert col.total_functions == 2
        assert len(col.fault_lines) == 1


class TestDiffResult:
    def test_no_quakes(self):
        dr = DiffResult(package="pkg", version_a="1.0", version_b="2.0")
        assert dr.has_quakes is False
        assert dr.unchanged_count == 0

    def test_with_quakes(self):
        dr = DiffResult(
            package="pkg",
            version_a="1.0",
            version_b="2.0",
            behavioral_quakes=[{"probe": "p1", "description": "changed"}],
        )
        assert dr.has_quakes is True


class TestScanResult:
    def test_no_hazards(self):
        sr = ScanResult(lockfile="test.lock", packages_scanned=5)
        assert sr.has_hazards is False

    def test_with_hazards(self):
        sr = ScanResult(
            lockfile="test.lock",
            fault_lines=[FaultLine("pkg", "a", "b", 90.0, 10.0)],
            packages_scanned=5,
        )
        assert sr.has_hazards is True

    def test_quicksand_is_hazard(self):
        sr = ScanResult(
            lockfile="test.lock",
            quicksand_zones=[BedrockReport("pkg", "fn", 10.0, 1, 10, 0.0)],
            packages_scanned=5,
        )
        assert sr.has_hazards is True

    def test_erosion_is_hazard(self):
        sr = ScanResult(
            lockfile="test.lock",
            erosion_warnings=[
                ErosionReport("pkg", "fn", -0.05, 1.0, 0.7, 5, True)
            ],
            packages_scanned=5,
        )
        assert sr.has_hazards is True
