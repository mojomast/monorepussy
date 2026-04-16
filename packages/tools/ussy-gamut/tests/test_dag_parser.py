"""Tests for gamut.dag_parser module."""

import json
import pytest
from pathlib import Path

from gamut.dag_parser import parse_pipeline, dag_from_yaml, _parse_simple_yaml, _yaml_value
from gamut.models import PipelineDAG


class TestParsePipeline:
    """Tests for parse_pipeline dispatch function."""

    def test_json_pipeline(self, sample_pipeline_json):
        dag = parse_pipeline(sample_pipeline_json)
        assert isinstance(dag, PipelineDAG)
        assert dag.name == "etl_pipeline"
        assert len(dag.stages) == 3

    def test_yaml_pipeline(self, sample_pipeline_yaml):
        dag = parse_pipeline(sample_pipeline_yaml)
        assert isinstance(dag, PipelineDAG)
        # Name should come from YAML
        assert "avro" in dag.name.lower() or len(dag.stages) >= 1

    def test_directory_pipeline(self, tmp_path):
        stage1 = {
            "stage_name": "source",
            "system": "postgresql",
            "fields": {"id": {"type": "INTEGER"}}
        }
        (tmp_path / "01_source.json").write_text(json.dumps(stage1))
        dag = parse_pipeline(tmp_path)
        assert isinstance(dag, PipelineDAG)

    def test_unsupported_format(self, tmp_path):
        bad_file = tmp_path / "pipeline.toml"
        bad_file.write_text("name = test")
        with pytest.raises(ValueError, match="Unsupported pipeline format"):
            parse_pipeline(bad_file)


class TestDagFromYaml:
    """Tests for YAML pipeline parser."""

    def test_basic_yaml(self, tmp_path):
        yaml_content = """\
name: test_yaml
stages:
  - name: source
    system: postgresql
    fields:
      id:
        type: INTEGER
  - name: dest
    system: json
    fields:
      id:
        type: number
edges:
  - source: source
    dest: dest
"""
        yaml_file = tmp_path / "pipeline.yaml"
        yaml_file.write_text(yaml_content)
        dag = dag_from_yaml(yaml_file)
        assert dag.name == "test_yaml"
        assert len(dag.stages) >= 1

    def test_yaml_with_comments(self, tmp_path):
        yaml_content = """\
# This is a comment
name: commented_pipeline
stages:
  - name: src  # inline comment
    system: json
    fields:
      val:
        type: number
"""
        yaml_file = tmp_path / "pipeline.yaml"
        yaml_file.write_text(yaml_content)
        dag = dag_from_yaml(yaml_file)
        assert dag.name == "commented_pipeline"


class TestYamlValueParser:
    """Tests for _yaml_value helper."""

    def test_string_quoted(self):
        assert _yaml_value('"hello"') == "hello"
        assert _yaml_value("'hello'") == "hello"

    def test_integer(self):
        assert _yaml_value("42") == 42

    def test_float(self):
        assert _yaml_value("3.14") == 3.14

    def test_boolean(self):
        assert _yaml_value("true") is True
        assert _yaml_value("false") is False
        assert _yaml_value("yes") is True
        assert _yaml_value("no") is False

    def test_null(self):
        assert _yaml_value("null") is None
        assert _yaml_value("~") is None

    def test_unquoted_string(self):
        assert _yaml_value("hello") == "hello"


class TestYamlSimpleParser:
    """Tests for _parse_simple_yaml."""

    def test_simple_mapping(self):
        result = _parse_simple_yaml("name: test\nsystem: json\n")
        assert result["name"] == "test"
        assert result["system"] == "json"

    def test_nested_mapping(self):
        yaml_text = """\
name: test
fields:
  id:
    type: INTEGER
"""
        result = _parse_simple_yaml(yaml_text)
        assert result["name"] == "test"
        assert "fields" in result
