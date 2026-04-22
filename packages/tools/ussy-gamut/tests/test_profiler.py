"""Tests for gamut.profiler module."""

import json
import pytest
from pathlib import Path

from gamut.models import FieldType, StageProfile, TypeGamut
from gamut.profiler import (
    get_profiler,
    profile_from_json,
    profile_stage,
    resolve_type,
    dag_from_json,
    dag_from_dir,
)
from gamut.systems import SYSTEM_PROFILERS


class TestGetProfiler:
    """Tests for get_profiler function."""

    def test_known_systems(self):
        for name in ["postgresql", "bigquery", "parquet", "protobuf", "json", "avro", "spark"]:
            p = get_profiler(name)
            assert p is not None, f"Missing profiler for {name}"

    def test_unknown_system(self):
        assert get_profiler("nonexistent") is None

    def test_case_insensitive(self):
        assert get_profiler("PostgreSQL") is not None
        assert get_profiler("JSON") is not None


class TestResolveType:
    """Tests for resolve_type function."""

    def test_postgresql_integer(self):
        g = resolve_type("postgresql", "INTEGER")
        assert g.field_type == FieldType.INTEGER
        assert g.min_value == -2147483648
        assert g.max_value == 2147483647

    def test_json_number(self):
        g = resolve_type("json", "number")
        assert g.field_type == FieldType.FLOAT
        assert g.precision == 15

    def test_unknown_system_returns_unknown(self):
        g = resolve_type("nonexistent", "whatever")
        assert g.field_type == FieldType.UNKNOWN

    def test_bigquery_int64(self):
        g = resolve_type("bigquery", "INT64")
        assert g.field_type == FieldType.INTEGER
        assert g.precision == 19


class TestProfileStage:
    """Tests for profile_stage function."""

    def test_postgresql_stage(self, postgres_stage):
        assert postgres_stage.name == "pg_source"
        assert postgres_stage.system == "postgresql"
        assert len(postgres_stage.fields) == 5

    def test_json_stage(self, json_stage):
        assert json_stage.name == "json_api"
        assert json_stage.system == "json"
        assert len(json_stage.fields) == 5

    def test_bigquery_stage(self, bigquery_stage):
        assert bigquery_stage.name == "bq_dest"
        assert bigquery_stage.system == "bigquery"
        assert len(bigquery_stage.fields) == 5

    def test_unknown_system_raises(self):
        with pytest.raises(ValueError, match="Unknown system"):
            profile_stage("nonexistent", "test", {})


class TestProfileFromJson:
    """Tests for profile_from_json function."""

    def test_load_postgres_stage(self, sample_postgres_stage_json):
        stage = profile_from_json(sample_postgres_stage_json)
        assert stage.name == "postgres_source"
        assert stage.system == "postgresql"
        assert len(stage.fields) == 4

    def test_field_types(self, sample_postgres_stage_json):
        stage = profile_from_json(sample_postgres_stage_json)
        field_map = {f.name: f for f in stage.fields}
        assert field_map["id"].gamut.field_type == FieldType.INTEGER
        assert field_map["amount"].gamut.field_type == FieldType.DECIMAL
        assert field_map["created_at"].gamut.field_type == FieldType.TIMESTAMP


class TestDagFromJson:
    """Tests for dag_from_json function."""

    def test_load_pipeline(self, sample_pipeline_json):
        dag = dag_from_json(sample_pipeline_json)
        assert dag.name == "etl_pipeline"
        assert len(dag.stages) == 3
        assert len(dag.edges) == 2

    def test_stages_populated(self, sample_pipeline_json):
        dag = dag_from_json(sample_pipeline_json)
        assert "postgres_source" in dag.stages
        assert "json_api" in dag.stages
        assert "bigquery_dest" in dag.stages

    def test_boundary_pairs(self, sample_pipeline_json):
        dag = dag_from_json(sample_pipeline_json)
        pairs = dag.boundary_pairs()
        assert len(pairs) == 2


class TestDagFromDir:
    """Tests for dag_from_dir function."""

    def test_from_directory(self, tmp_path):
        # Create stage files
        stage1 = {
            "stage_name": "stage_a",
            "system": "postgresql",
            "fields": {"id": {"type": "INTEGER"}}
        }
        stage2 = {
            "stage_name": "stage_b",
            "system": "json",
            "fields": {"id": {"type": "number"}}
        }
        (tmp_path / "01_stage_a.json").write_text(json.dumps(stage1))
        (tmp_path / "02_stage_b.json").write_text(json.dumps(stage2))

        dag = dag_from_dir(tmp_path)
        assert len(dag.stages) == 2
        assert len(dag.edges) == 1  # Inferred from alphabetical order

    def test_with_pipeline_file(self, tmp_path):
        stage1 = {
            "stage_name": "source",
            "system": "postgresql",
            "fields": {"id": {"type": "INTEGER"}}
        }
        stage2 = {
            "stage_name": "dest",
            "system": "json",
            "fields": {"id": {"type": "number"}}
        }
        pipeline = {
            "name": "custom_pipeline",
            "edges": [{"source": "source", "dest": "dest"}]
        }
        (tmp_path / "source.json").write_text(json.dumps(stage1))
        (tmp_path / "dest.json").write_text(json.dumps(stage2))
        (tmp_path / "_pipeline.json").write_text(json.dumps(pipeline))

        dag = dag_from_dir(tmp_path)
        assert dag.name == "custom_pipeline"
        assert len(dag.edges) == 1

    def test_not_directory_raises(self):
        with pytest.raises(ValueError, match="Not a directory"):
            dag_from_dir("/nonexistent/path")


class TestSystemProfilersCompleteness:
    """Ensure all system profilers cover key types."""

    def test_all_systems_registered(self):
        expected = {"postgresql", "bigquery", "parquet", "protobuf", "json", "avro", "spark"}
        assert set(SYSTEM_PROFILERS.keys()) == expected

    def test_postgresql_key_types(self):
        pg = get_profiler("postgresql")
        for tn in ["INTEGER", "BIGINT", "NUMERIC(38,18)", "TIMESTAMPTZ", "VARCHAR(255)", "TEXT", "BOOLEAN"]:
            g = pg.resolve_type(tn)
            assert g.field_type != FieldType.UNKNOWN, f"PostgreSQL {tn} should not be UNKNOWN"

    def test_bigquery_key_types(self):
        bq = get_profiler("bigquery")
        for tn in ["INT64", "FLOAT64", "NUMERIC", "STRING", "TIMESTAMP", "BOOL"]:
            g = bq.resolve_type(tn)
            assert g.field_type != FieldType.UNKNOWN, f"BigQuery {tn} should not be UNKNOWN"

    def test_json_key_types(self):
        jp = get_profiler("json")
        for tn in ["number", "string", "boolean", "null", "array", "object"]:
            g = jp.resolve_type(tn)
            assert g.system == "json"

    def test_avro_key_types(self):
        ap = get_profiler("avro")
        for tn in ["int", "long", "float", "double", "string", "bytes", "boolean", "null"]:
            g = ap.resolve_type(tn)
            assert g.system == "avro"

    def test_spark_key_types(self):
        sp = get_profiler("spark")
        for tn in ["int", "long", "double", "string", "boolean", "date", "timestamp"]:
            g = sp.resolve_type(tn)
            assert g.system == "spark"

    def test_parquet_key_types(self):
        pp = get_profiler("parquet")
        for tn in ["int32", "int64", "float", "double", "utf8", "binary", "boolean"]:
            g = pp.resolve_type(tn)
            assert g.system == "parquet"

    def test_protobuf_key_types(self):
        pbp = get_profiler("protobuf")
        for tn in ["int32", "int64", "float", "double", "string", "bytes", "bool"]:
            g = pbp.resolve_type(tn)
            assert g.system == "protobuf"
