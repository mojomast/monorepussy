"""Tests for chromato.engine — Full pipeline integration."""

import pytest
from pathlib import Path

from chromato.engine import compute_max_risk, run_diff, run_scan
from chromato.models import Solvent


FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestRunScan:
    def test_scan_requirements_txt(self):
        result = run_scan(str(FIXTURES / "requirements.txt"))
        assert result.source == str(FIXTURES / "requirements.txt")
        assert len(result.peaks) > 0
        assert result.solvent == Solvent.COUPLING

    def test_scan_package_json(self):
        result = run_scan(str(FIXTURES / "package.json"))
        assert len(result.peaks) > 0

    def test_scan_cargo_toml(self):
        result = run_scan(str(FIXTURES / "Cargo.toml"))
        assert len(result.peaks) > 0

    def test_scan_go_mod(self):
        result = run_scan(str(FIXTURES / "go.mod"))
        assert len(result.peaks) > 0

    def test_scan_pom_xml(self):
        result = run_scan(str(FIXTURES / "pom.xml"))
        assert len(result.peaks) > 0

    def test_scan_gemspec(self):
        result = run_scan(str(FIXTURES / "test.gemspec"))
        assert len(result.peaks) > 0

    def test_scan_with_risk_solvent(self):
        result = run_scan(str(FIXTURES / "requirements.txt"), solvent=Solvent.RISK)
        assert result.solvent == Solvent.RISK
        for peak in result.peaks:
            assert peak.retention_time >= 0.0

    def test_scan_with_freshness_solvent(self):
        result = run_scan(str(FIXTURES / "requirements.txt"), solvent=Solvent.FRESHNESS)
        assert result.solvent == Solvent.FRESHNESS

    def test_scan_with_license_solvent(self):
        result = run_scan(str(FIXTURES / "requirements.txt"), solvent=Solvent.LICENSE)
        assert result.solvent == Solvent.LICENSE

    def test_scan_directory(self):
        result = run_scan(str(FIXTURES))
        assert len(result.peaks) > 0

    def test_scan_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            run_scan("/nonexistent/file.txt")

    def test_scan_peaks_sorted_by_retention_time(self):
        result = run_scan(str(FIXTURES / "requirements.txt"))
        rts = [p.retention_time for p in result.peaks]
        assert rts == sorted(rts)


class TestRunDiff:
    def test_basic_diff(self):
        result_a, result_b = run_diff(
            str(FIXTURES / "requirements.txt"),
            str(FIXTURES / "requirements-new.txt"),
        )
        assert len(result_a.peaks) > 0
        assert len(result_b.peaks) > 0

    def test_diff_different_counts(self):
        result_a, result_b = run_diff(
            str(FIXTURES / "requirements.txt"),
            str(FIXTURES / "requirements-new.txt"),
        )
        # requirements.txt has 10 deps, requirements-new.txt has 9
        assert len(result_a.peaks) >= len(result_b.peaks)


class TestComputeMaxRisk:
    def test_with_peaks_coupling(self):
        result = run_scan(str(FIXTURES / "requirements.txt"), solvent=Solvent.LICENSE)
        max_risk = compute_max_risk(result)
        # With license solvent, UNKNOWN licenses get 0.6 retention time
        assert max_risk >= 0.0

    def test_with_peaks_risk_solvent(self):
        result = run_scan(str(FIXTURES / "requirements.txt"), solvent=Solvent.RISK)
        max_risk = compute_max_risk(result)
        # With risk solvent and no advisory data, days_since_update=9999
        # gives 0.005 * 9999 = 49.995 for each dep
        assert max_risk > 0.0

    def test_empty_result(self):
        from chromato.models import ChromatogramResult
        result = ChromatogramResult()
        max_risk = compute_max_risk(result)
        assert max_risk == 0.0
