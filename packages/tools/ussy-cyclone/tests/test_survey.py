"""Tests for cyclone.survey — pipeline topology discovery."""

import json
import os
import tempfile

import pytest

from cyclone.survey import (
    discover_config,
    format_survey,
    load_topology,
    survey,
)
from cyclone.models import PipelineTopology


@pytest.fixture
def pipeline_config():
    return {
        "stages": [
            {
                "name": "ingest",
                "type": "kafka",
                "forward_rate": 5000.0,
                "reprocessing_rate": 50.0,
                "queue_depth": 200,
                "consumer_count": 4,
            },
            {
                "name": "process",
                "type": "generic",
                "forward_rate": 4000.0,
                "reprocessing_rate": 200.0,
                "queue_depth": 500,
                "consumer_count": 3,
            },
        ],
        "edges": [["ingest", "process"]],
        "retry_edges": [],
    }


@pytest.fixture
def config_dir(pipeline_config):
    """Create a temporary directory with a pipeline.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "pipeline.json")
        with open(path, "w") as f:
            json.dump(pipeline_config, f)
        yield tmpdir


class TestDiscoverConfig:
    def test_finds_pipeline_json(self, config_dir):
        result = discover_config(config_dir)
        assert result is not None
        assert result.endswith("pipeline.json")

    def test_not_found_in_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert discover_config(tmpdir) is None

    def test_not_a_directory(self):
        assert discover_config("/nonexistent/path") is None

    def test_finds_cyclone_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cyclone.json")
            with open(path, "w") as f:
                f.write("{}")
            result = discover_config(tmpdir)
            assert result is not None

    def test_finds_by_name_pattern(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "my_pipeline_config.json")
            with open(path, "w") as f:
                f.write("{}")
            result = discover_config(tmpdir)
            assert result is not None


class TestLoadTopology:
    def test_from_file(self, pipeline_config):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(pipeline_config, f)
            path = f.name
        try:
            topo = load_topology(path)
            assert isinstance(topo, PipelineTopology)
            assert len(topo.stages) == 2
        finally:
            os.unlink(path)

    def test_from_directory(self, config_dir):
        topo = load_topology(config_dir)
        assert isinstance(topo, PipelineTopology)
        assert len(topo.stages) == 2

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_topology("/nonexistent/file.json")

    def test_dir_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                load_topology(tmpdir)


class TestSurvey:
    def test_survey_returns_summary(self, config_dir):
        result = survey(config_dir)
        assert "topology" in result
        assert "stage_count" in result
        assert "edge_count" in result
        assert result["stage_count"] == 2
        assert result["edge_count"] == 1

    def test_survey_stages_list(self, config_dir):
        result = survey(config_dir)
        assert len(result["stages"]) == 2
        assert result["stages"][0]["name"] == "ingest"


class TestFormatSurvey:
    def test_format_produces_output(self, config_dir):
        result = survey(config_dir)
        output = format_survey(result)
        assert "CYCLONE" in output
        assert "ingest" in output
        assert "process" in output

    def test_format_includes_edges(self, config_dir):
        result = survey(config_dir)
        output = format_survey(result)
        assert "→" in output
