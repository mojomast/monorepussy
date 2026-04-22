"""Shared test fixtures."""

import json
from pathlib import Path

import pytest

from ussy_gamut.models import (
    ClippingRisk,
    FieldType,
    FieldProfile,
    PipelineDAG,
    RenderingIntent,
    StageProfile,
    TypeGamut,
)
from ussy_gamut.profiler import profile_stage


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def postgres_stage():
    """A PostgreSQL stage profile."""
    return profile_stage("postgresql", "pg_source", {
        "id": {"type": "BIGINT", "nullable": False},
        "amount": {"type": "NUMERIC(38,18)"},
        "created_at": {"type": "TIMESTAMPTZ"},
        "description": {"type": "VARCHAR(500)"},
        "is_active": {"type": "BOOLEAN"},
    })


@pytest.fixture
def json_stage():
    """A JSON stage profile."""
    return profile_stage("json", "json_api", {
        "id": {"type": "number"},
        "amount": {"type": "number"},
        "created_at": {"type": "string"},
        "description": {"type": "string"},
        "is_active": {"type": "boolean"},
    })


@pytest.fixture
def bigquery_stage():
    """A BigQuery stage profile."""
    return profile_stage("bigquery", "bq_dest", {
        "id": {"type": "INT64"},
        "amount": {"type": "NUMERIC(38,9)"},
        "created_at": {"type": "DATETIME"},
        "description": {"type": "STRING"},
        "is_active": {"type": "BOOL"},
    })


@pytest.fixture
def sample_dag():
    """A sample PipelineDAG with three stages."""
    pg = profile_stage("postgresql", "postgres", {
        "id": {"type": "BIGINT"},
        "amount": {"type": "NUMERIC(38,18)"},
        "created_at": {"type": "TIMESTAMPTZ"},
    })
    js = profile_stage("json", "json_api", {
        "id": {"type": "number"},
        "amount": {"type": "number"},
        "created_at": {"type": "string"},
    })
    bq = profile_stage("bigquery", "bigquery", {
        "id": {"type": "INT64"},
        "amount": {"type": "NUMERIC(38,9)"},
        "created_at": {"type": "DATETIME"},
    })
    dag = PipelineDAG(name="test_pipeline")
    dag.add_stage(pg)
    dag.add_stage(js)
    dag.add_stage(bq)
    dag.add_edge("postgres", "json_api")
    dag.add_edge("json_api", "bigquery")
    return dag


@pytest.fixture
def sample_pipeline_json():
    """Path to the sample pipeline JSON fixture."""
    return FIXTURES_DIR / "sample_pipeline.json"


@pytest.fixture
def sample_pipeline_yaml():
    """Path to the sample pipeline YAML fixture."""
    return FIXTURES_DIR / "sample_pipeline.yaml"


@pytest.fixture
def sample_data_csv():
    """Path to the sample CSV data fixture."""
    return FIXTURES_DIR / "sample_data.csv"


@pytest.fixture
def sample_data_json():
    """Path to the sample JSON data fixture."""
    return FIXTURES_DIR / "sample_data.json"


@pytest.fixture
def sample_postgres_stage_json():
    """Path to the single stage JSON fixture."""
    return FIXTURES_DIR / "postgres_stage.json"
