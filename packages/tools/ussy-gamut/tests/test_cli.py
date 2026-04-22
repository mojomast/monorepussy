"""Tests for gamut.cli module."""

import pytest
from pathlib import Path

from ussy_gamut.cli import main, build_parser


class TestBuildParser:
    """Tests for CLI argument parser."""

    def test_parser_creates(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    def test_no_command_returns_0(self):
        result = main([])
        assert result == 0


class TestProfileCommand:
    """Tests for profile subcommand."""

    def test_profile_system_type(self, capsys):
        result = main(["profile", "--system", "postgresql", "--type-name", "INTEGER"])
        assert result == 0
        captured = capsys.readouterr()
        assert "INTEGER" in captured.out
        assert "postgresql" in captured.out

    def test_profile_input_json(self, capsys, sample_pipeline_json):
        result = main(["profile", "--input", str(sample_pipeline_json)])
        assert result == 0
        captured = capsys.readouterr()
        assert "etl_pipeline" in captured.out

    def test_profile_no_args(self, capsys):
        result = main(["profile"])
        assert result == 1


class TestAnalyzeCommand:
    """Tests for analyze subcommand."""

    def test_analyze_json(self, capsys, sample_pipeline_json):
        result = main(["analyze", str(sample_pipeline_json)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Pipeline" in captured.out

    def test_analyze_detailed(self, capsys, sample_pipeline_json):
        result = main(["analyze", str(sample_pipeline_json), "--detailed"])
        assert result == 0

    def test_analyze_with_output(self, capsys, sample_pipeline_json, tmp_path):
        output_file = tmp_path / "results.json"
        result = main(["analyze", str(sample_pipeline_json), "--output", str(output_file)])
        assert result == 0
        assert output_file.exists()
        import json
        with open(output_file) as f:
            data = json.load(f)
        assert "boundaries" in data


class TestVisualizeCommand:
    """Tests for visualize subcommand."""

    def test_visualize(self, capsys, sample_pipeline_json):
        result = main(["visualize", str(sample_pipeline_json)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Gamut Diagram" in captured.out


class TestSampleCommand:
    """Tests for sample subcommand."""

    def test_sample_csv(self, capsys, sample_pipeline_json, sample_data_csv):
        result = main([
            "sample", str(sample_pipeline_json),
            "--data", str(sample_data_csv),
        ])
        assert result == 0

    def test_sample_json(self, capsys, sample_pipeline_json, sample_data_json):
        result = main([
            "sample", str(sample_pipeline_json),
            "--data", str(sample_data_json),
        ])
        assert result == 0
