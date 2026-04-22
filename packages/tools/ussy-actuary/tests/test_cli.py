"""Tests for actuary.cli — Command-Line Interface."""

import json
import pytest
from ussy_actuary.cli import build_parser, main


class TestBuildParser:
    """Tests for build_parser."""

    def test_parser_creation(self):
        parser = build_parser()
        assert parser is not None

    def test_survival_command(self):
        parser = build_parser()
        args = parser.parse_args(["survival", "--cohort", "Q1-2025"])
        assert args.command == "survival"
        assert args.cohort == "Q1-2025"

    def test_backlog_command(self):
        parser = build_parser()
        args = parser.parse_args(["backlog", "--repo", "./my-project", "--quarters", "8"])
        assert args.command == "backlog"
        assert args.repo == "./my-project"
        assert args.quarters == 8

    def test_credibility_command(self):
        parser = build_parser()
        args = parser.parse_args(["credibility", "--org", "myorg", "--n-obs", "52"])
        assert args.command == "credibility"
        assert args.org == "myorg"
        assert args.n_obs == 52

    def test_ibnr_command(self):
        parser = build_parser()
        args = parser.parse_args(["ibnr", "--density", "15.0", "--kloc", "10.0", "--reported", "3"])
        assert args.command == "ibnr"
        assert args.density == 15.0
        assert args.kloc == 10.0
        assert args.reported == 3

    def test_aggregate_command(self):
        parser = build_parser()
        args = parser.parse_args(["aggregate", "--assets", "100", "--copula", "clayton", "--alpha", "2.0"])
        assert args.command == "aggregate"
        assert args.assets == 100
        assert args.copula == "clayton"
        assert args.alpha == 2.0

    def test_moral_hazard_command(self):
        parser = build_parser()
        args = parser.parse_args(["moral-hazard", "--loss", "1000000", "--coverage", "0.8"])
        assert args.command == "moral-hazard"
        assert args.loss == 1000000
        assert args.coverage == 0.8

    def test_json_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--json", "survival"])
        assert args.json is True

    def test_ibnr_method_choices(self):
        parser = build_parser()
        args = parser.parse_args(["ibnr", "--method", "cape-cod"])
        assert args.method == "cape-cod"


class TestCLISurvival:
    """Tests for the survival command via CLI."""

    def test_survival_output(self, capsys):
        main(["survival", "--cohort", "test-cohort"])
        captured = capsys.readouterr()
        assert "Life Table for CVE Cohort: test-cohort" in captured.out

    def test_survival_json(self, capsys):
        main(["--json", "survival", "--cohort", "test-cohort"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "cohort_id" in data
        assert "rows" in data
        assert len(data["rows"]) > 0

    def test_survival_with_graduation(self, capsys):
        main(["survival", "--cohort", "test", "--lambda", "2.0"])
        captured = capsys.readouterr()
        assert "Life Table" in captured.out


class TestCLIBacklog:
    """Tests for the backlog command via CLI."""

    def test_backlog_output(self, capsys):
        main(["backlog", "--repo", "test-repo"])
        captured = capsys.readouterr()
        assert "Vulnerability Development Triangle" in captured.out
        assert "Age-to-age factors" in captured.out

    def test_backlog_json(self, capsys):
        main(["--json", "backlog", "--repo", "test-repo"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "age_to_age_factors" in data
        assert "total_reserve" in data


class TestCLICredibility:
    """Tests for the credibility command via CLI."""

    def test_credibility_output(self, capsys):
        main(["credibility", "--org", "myorg", "--n-obs", "52"])
        captured = capsys.readouterr()
        assert "Credibility Analysis" in captured.out
        assert "myorg" in captured.out

    def test_credibility_json(self, capsys):
        main(["--json", "credibility", "--org", "myorg", "--n-obs", "52"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "Z" in data
        assert data["n_obs"] == 52

    def test_credibility_with_params(self, capsys):
        main(["credibility", "--org", "test", "--epv", "0.01", "--vhm", "0.001"])
        captured = capsys.readouterr()
        assert "Credibility" in captured.out


class TestCLIIBNR:
    """Tests for the ibnr command via CLI."""

    def test_ibnr_output(self, capsys):
        main(["ibnr", "--density", "15.0", "--kloc", "10.0", "--reported", "3"])
        captured = capsys.readouterr()
        assert "IBNR" in captured.out

    def test_ibnr_json(self, capsys):
        main(["--json", "ibnr", "--density", "15.0", "--kloc", "10.0", "--reported", "3"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[0]["reported_count"] == 3

    def test_ibnr_cape_cod(self, capsys):
        main(["ibnr", "--method", "cape-cod"])
        captured = capsys.readouterr()
        assert "CAPE_COD" in captured.out.upper() or "IBNR" in captured.out


class TestCLIAggregate:
    """Tests for the aggregate command via CLI."""

    def test_aggregate_output(self, capsys):
        main(["aggregate", "--assets", "50", "--copula", "independent", "--sims", "1000"])
        captured = capsys.readouterr()
        assert "Correlated Risk Aggregation" in captured.out

    def test_aggregate_json(self, capsys):
        main(["--json", "aggregate", "--assets", "50", "--sims", "1000"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "var_value" in data
        assert "tvar_value" in data

    def test_aggregate_clayton(self, capsys):
        main(["aggregate", "--copula", "clayton", "--alpha", "2.0", "--sims", "500"])
        captured = capsys.readouterr()
        assert "clayton" in captured.out

    def test_aggregate_gumbel(self, capsys):
        main(["aggregate", "--copula", "gumbel", "--beta", "2.0", "--sims", "500"])
        captured = capsys.readouterr()
        assert "gumbel" in captured.out


class TestCLIMoralHazard:
    """Tests for the moral-hazard command via CLI."""

    def test_moral_hazard_output(self, capsys):
        main(["moral-hazard", "--loss", "1000000", "--coverage", "0.8"])
        captured = capsys.readouterr()
        assert "Moral Hazard" in captured.out
        assert "80.0%" in captured.out

    def test_moral_hazard_json(self, capsys):
        main(["--json", "moral-hazard", "--loss", "1000000", "--coverage", "0.8"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "effort_reduction_pct" in data
        assert "welfare_loss" in data

    def test_moral_hazard_sla(self, capsys):
        main(["moral-hazard", "--loss", "1000000", "--coverage", "0.9", "--sla-penalty", "100000"])
        captured = capsys.readouterr()
        assert "SLA" in captured.out


class TestCLIHelp:
    """Tests for help and no-command behavior."""

    def test_no_command(self, capsys):
        main([])
        captured = capsys.readouterr()
        assert "actuary" in captured.out.lower() or "usage" in captured.out.lower()

    def test_help_flag(self):
        parser = build_parser()
        # Just verify it doesn't crash
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0
