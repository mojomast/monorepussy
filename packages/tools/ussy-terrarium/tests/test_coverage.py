"""Tests for the coverage parsing module."""

import json
import os
import tempfile

import pytest

from terrarium.metrics.coverage import (
    parse_coverage_json,
    parse_coverage_lcov,
    auto_detect_coverage,
)


class TestParseCoverageJson:
    """Tests for coverage.json parsing."""

    def test_parse_valid_coverage(self):
        """Parse a valid coverage.json file."""
        data = {
            "files": {
                "src/main.py": {"summary": {"covered_lines": 8, "num_statements": 10}},
                "src/utils.py": {"summary": {"covered_lines": 10, "num_statements": 10}},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            result = parse_coverage_json(filepath)
            assert "src/main.py" in result
            assert abs(result["src/main.py"] - 0.8) < 0.01
            assert "src/utils.py" in result
            assert abs(result["src/utils.py"] - 1.0) < 0.01
        finally:
            os.unlink(filepath)

    def test_parse_zero_statements(self):
        """File with zero statements gets 100% coverage."""
        data = {
            "files": {
                "empty.py": {"summary": {"covered_lines": 0, "num_statements": 0}},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            result = parse_coverage_json(filepath)
            assert result["empty.py"] == 1.0
        finally:
            os.unlink(filepath)

    def test_parse_invalid_json(self):
        """Invalid JSON returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json {{{")
            filepath = f.name

        try:
            result = parse_coverage_json(filepath)
            assert result == {}
        finally:
            os.unlink(filepath)

    def test_parse_nonexistent_file(self):
        """Non-existent file returns empty dict."""
        result = parse_coverage_json("/nonexistent/coverage.json")
        assert result == {}

    def test_parse_fixture_coverage(self):
        """Parse the test fixture coverage.json."""
        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "coverage.json"
        )
        if os.path.exists(fixture_path):
            result = parse_coverage_json(fixture_path)
            assert "src/main.py" in result
            assert "src/auth.py" in result


class TestParseCoverageLcov:
    """Tests for lcov .info file parsing."""

    def test_parse_lcov(self):
        """Parse a simple lcov info file."""
        lcov_content = """TN:
SF:src/main.py
DA:1,1
DA:2,1
DA:3,0
DA:4,1
end_of_record
SF:src/utils.py
DA:1,1
DA:2,1
end_of_record
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".info", delete=False) as f:
            f.write(lcov_content)
            filepath = f.name

        try:
            result = parse_coverage_lcov(filepath)
            assert "src/main.py" in result
            assert abs(result["src/main.py"] - 0.75) < 0.01
            assert "src/utils.py" in result
            assert abs(result["src/utils.py"] - 1.0) < 0.01
        finally:
            os.unlink(filepath)

    def test_parse_lcov_nonexistent(self):
        """Non-existent lcov file returns empty dict."""
        result = parse_coverage_lcov("/nonexistent/file.info")
        assert result == {}


class TestAutoDetectCoverage:
    """Tests for automatic coverage report detection."""

    def test_detect_coverage_json(self):
        """Auto-detect coverage.json in project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "files": {
                    "main.py": {"summary": {"covered_lines": 5, "num_statements": 10}},
                }
            }
            with open(os.path.join(tmpdir, "coverage.json"), "w") as f:
                json.dump(data, f)

            result = auto_detect_coverage(tmpdir)
            assert "main.py" in result

    def test_no_coverage_report(self):
        """Directory with no coverage reports returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = auto_detect_coverage(tmpdir)
            assert result == {}
