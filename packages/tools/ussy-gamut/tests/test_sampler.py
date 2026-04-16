"""Tests for gamut.sampler module."""

import json
import pytest
from pathlib import Path

from gamut.models import FieldType, SampleReport, SampleValue, TypeGamut
from gamut.profiler import profile_stage
from gamut.sampler import (
    format_sample_report,
    load_csv_data,
    load_json_data,
    sample_boundary,
    _is_value_clipped,
    _predict_clipping,
    _auto_convert,
)


class TestSampleBoundary:
    """Tests for sample_boundary function."""

    def test_predict_clipping(self, postgres_stage, json_stage):
        source_data = [
            {"id": 1, "amount": 123.456, "created_at": "2024-01-01", "description": "test", "is_active": True},
        ]
        report = sample_boundary(postgres_stage, json_stage, source_data)
        assert report.total_count == 5  # 5 fields
        assert report.source_stage == "pg_source"

    def test_with_dest_data(self, postgres_stage, json_stage):
        source_data = [
            {"id": 1, "amount": 123.456, "created_at": "2024-01-01", "description": "test", "is_active": True},
        ]
        dest_data = [
            {"id": 1, "amount": 123.456, "created_at": "2024-01-01", "description": "test", "is_active": True},
        ]
        report = sample_boundary(postgres_stage, json_stage, source_data, dest_data)
        assert report.total_count == 5

    def test_clipping_detected(self):
        src = profile_stage("postgresql", "src", {"val": {"type": "INTEGER"}})
        dst = profile_stage("postgresql", "dst", {"val": {"type": "SMALLINT"}})
        # Value outside SMALLINT range
        source_data = [{"val": 100000}]
        report = sample_boundary(src, dst, source_data)
        assert report.clipped_count >= 1


class TestPredictClipping:
    """Tests for _predict_clipping function."""

    def test_in_range(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                      min_value=-32768, max_value=32767)
        assert not _predict_clipping(100, g)

    def test_out_of_range_high(self):
        g = TypeGamut(system="pg", type_name="SMALLINT", field_type=FieldType.INTEGER,
                      min_value=-32768, max_value=32767)
        assert _predict_clipping(100000, g)

    def test_out_of_range_low(self):
        g = TypeGamut(system="pg", type_name="SMALLINT", field_type=FieldType.INTEGER,
                      min_value=-32768, max_value=32767)
        assert _predict_clipping(-100000, g)

    def test_null_in_nullable(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=True)
        assert not _predict_clipping(None, g)

    def test_null_in_not_nullable(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=False)
        assert _predict_clipping(None, g)

    def test_string_length_ok(self):
        g = TypeGamut(system="pg", type_name="VARCHAR(100)", field_type=FieldType.STRING,
                      max_length=100)
        assert not _predict_clipping("short", g)

    def test_string_too_long(self):
        g = TypeGamut(system="pg", type_name="VARCHAR(5)", field_type=FieldType.STRING,
                      max_length=5)
        assert _predict_clipping("this is too long", g)


class TestIsValueClipped:
    """Tests for _is_value_clipped function."""

    def test_same_values(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        assert not _is_value_clipped(42, 42, g)

    def test_different_values_numeric(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        assert _is_value_clipped(42, 40, g)

    def test_value_to_null(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        assert _is_value_clipped(42, None, g)

    def test_null_to_value(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        assert not _is_value_clipped(None, 42, g)

    def test_both_null(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        assert not _is_value_clipped(None, None, g)


class TestAutoConvert:
    """Tests for _auto_convert helper."""

    def test_integer(self):
        assert _auto_convert("42") == 42
        assert isinstance(_auto_convert("42"), int)

    def test_float(self):
        assert _auto_convert("3.14") == 3.14
        assert isinstance(_auto_convert("3.14"), float)

    def test_boolean_true(self):
        assert _auto_convert("true") is True
        assert _auto_convert("True") is True

    def test_boolean_false(self):
        assert _auto_convert("false") is False

    def test_string(self):
        assert _auto_convert("hello") == "hello"


class TestLoadCsvData:
    """Tests for load_csv_data function."""

    def test_load_fixture(self, sample_data_csv):
        data = load_csv_data(sample_data_csv)
        assert len(data) == 5
        assert "id" in data[0]
        assert "amount" in data[0]

    def test_auto_conversion(self, sample_data_csv):
        data = load_csv_data(sample_data_csv)
        assert isinstance(data[0]["id"], int)


class TestLoadJsonData:
    """Tests for load_json_data function."""

    def test_load_fixture(self, sample_data_json):
        data = load_json_data(sample_data_json)
        assert len(data) == 3
        assert "id" in data[0]

    def test_single_object(self, tmp_path):
        obj = {"key": "value"}
        f = tmp_path / "data.json"
        f.write_text(json.dumps(obj))
        data = load_json_data(f)
        assert len(data) == 1


class TestFormatSampleReport:
    """Tests for format_sample_report function."""

    def test_empty_report(self):
        report = SampleReport(source_stage="a", dest_stage="b")
        output = format_sample_report(report)
        assert "Total samples : 0" in output

    def test_with_samples(self):
        samples = [
            SampleValue(field_name="f1", value=1, stage="b", is_clipped=False),
            SampleValue(field_name="f2", value=2, stage="b", is_clipped=True),
        ]
        report = SampleReport(source_stage="a", dest_stage="b", samples=samples)
        output = format_sample_report(report)
        assert "Total samples : 2" in output
        assert "Clipped       : 1" in output
