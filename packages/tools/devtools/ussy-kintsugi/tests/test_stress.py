"""Tests for the stress testing module."""

import os
import tempfile
from pathlib import Path

import pytest

from kintsugi.joint import Joint, JointStore
from kintsugi.stress import (
    LineCommenter,
    comment_out_line,
    StressResult,
    StressReport,
    stress_test_joint,
    write_junit_xml,
)


class TestLineCommenter:
    """Test the AST-based LineCommenter."""

    def test_comment_out_return(self):
        source = "def foo():\n    return 42\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_assign(self):
        source = "x = 1\ny = 2\n"
        modified, found = comment_out_line(source, 1)
        assert found is True

    def test_line_not_found(self):
        source = "x = 1\n"
        modified, found = comment_out_line(source, 99)
        assert found is False

    def test_comment_out_if(self):
        source = "def foo(x):\n    if x is not None:\n        return x.lower()\n    return ''\n"
        modified, found = comment_out_line(source, 2)
        assert found is True

    def test_comment_out_annassign(self):
        source = "class Foo:\n    def __init__(self, x):\n        self.value: int = x\n"
        modified, found = comment_out_line(source, 3)
        assert found is True
        assert "pass" in modified

    def test_comment_out_delete(self):
        source = "cache = {}\ndel cache\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_with(self):
        source = "def read(path):\n    with open(path) as f:\n        data = f.read()\n    return data\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_asyncwith(self):
        source = "async def read(path):\n    async with open(path) as f:\n        data = await f.read()\n    return data\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_for(self):
        source = "def process(items):\n    for item in items:\n        print(item)\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_while(self):
        source = "def countdown(n):\n    while n > 0:\n        n -= 1\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_try(self):
        source = "def safe_div(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return 0\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_comment_out_inside_async_function(self):
        source = "async def handler():\n    result = await fetch()\n    return result\n"
        modified, found = comment_out_line(source, 2)
        assert found is True
        assert "pass" in modified

    def test_no_ast_flag_uses_text_fallback(self):
        source = "x = 1\ny = 2\n"
        modified, found = comment_out_line(source, 1, no_ast=True)
        assert found is True
        assert "KINTSUGI_REMOVED" in modified
        # Text fallback preserves line structure with a comment prefix
        lines = modified.splitlines()
        assert lines[0].startswith("# KINTSUGI_REMOVED:")
        # Second line is untouched
        assert lines[1] == "y = 2"


class TestCommentOutLine:
    """Test text-based fallback for commenting out lines."""

    def test_fallback_on_syntax_error(self):
        source = "this is not valid python {{{\n"
        modified, found = comment_out_line(source, 1)
        # Should use text-based fallback
        assert found is True
        assert "KINTSUGI_REMOVED" in modified

    def test_line_out_of_range(self):
        source = "x = 1\n"
        modified, found = comment_out_line(source, 5)
        assert found is False


class TestStressResult:
    """Test StressResult dataclass."""

    def test_default_values(self):
        r = StressResult()
        assert r.outcome == "untested"
        assert r.joint_id == ""

    def test_with_values(self):
        r = StressResult(joint_id="j-test", outcome="solid_gold", message="still needed")
        assert r.joint_id == "j-test"
        assert r.outcome == "solid_gold"


class TestStressReport:
    """Test StressReport dataclass."""

    def test_empty_report(self):
        report = StressReport()
        assert report.total == 0
        assert report.solid_count == 0
        assert report.hollow_count == 0

    def test_counts(self):
        report = StressReport(results=[
            StressResult(outcome="solid_gold"),
            StressResult(outcome="solid_gold"),
            StressResult(outcome="hollow"),
            StressResult(outcome="error"),
            StressResult(outcome="untested"),
        ])
        assert report.solid_count == 2
        assert report.hollow_count == 1
        assert report.error_count == 1
        assert report.untested_count == 1
        assert report.total == 5

    def test_to_dict(self):
        report = StressReport(results=[
            StressResult(joint_id="j-1", outcome="solid_gold"),
        ])
        d = report.to_dict()
        assert d["total"] == 1
        assert d["solid_gold"] == 1
        assert len(d["results"]) == 1


class TestStressTestJoint:
    """Test stress-testing individual joints."""

    def test_joint_without_test_ref(self):
        j = Joint(id="j-test", file="test.py", line=1, test_ref="", timestamp="2024-01-01T00:00:00+00:00")
        result = stress_test_joint(j)
        assert result.outcome == "untested"

    def test_joint_without_file(self):
        j = Joint(id="j-test", file="", line=1, test_ref="test_foo", timestamp="2024-01-01T00:00:00+00:00")
        result = stress_test_joint(j)
        assert result.outcome == "error"

    def test_joint_file_not_found(self):
        j = Joint(id="j-test", file="/nonexistent/file.py", line=1, test_ref="test_foo", timestamp="2024-01-01T00:00:00+00:00")
        result = stress_test_joint(j, project_root="/nonexistent")
        assert result.outcome == "error"

    def test_joint_with_real_file(self, tmp_path):
        """Test with a real file but no actual test runner available."""
        f = tmp_path / "test_module.py"
        f.write_text("def foo():\n    x = 1\n    return x\n")

        j = Joint(
            id="j-test",
            file="test_module.py",
            line=2,
            test_ref="test_foo",
            timestamp="2024-01-01T00:00:00+00:00",
        )
        # This will try to run pytest which may not be available, but it should
        # at least process the file without crashing
        result = stress_test_joint(j, project_root=str(tmp_path))
        # The outcome depends on whether pytest is available
        assert result.outcome in ("solid_gold", "hollow", "error")
        # Original file should be restored
        content = f.read_text()
        assert "x = 1" in content


class TestWriteJunitXml:
    """Test JUnit XML output."""

    def test_write_junit_xml(self, tmp_path):
        report = StressReport(results=[
            StressResult(joint_id="j-1", file="test.py", line=1, test_ref="test_a", outcome="solid_gold", message="still needed"),
            StressResult(joint_id="j-2", file="test.py", line=2, test_ref="test_b", outcome="hollow", message="redundant"),
            StressResult(joint_id="j-3", file="test.py", line=3, test_ref="test_c", outcome="error", message="file not found"),
            StressResult(joint_id="j-4", file="test.py", line=4, test_ref="", outcome="untested", message="no test ref"),
        ])

        output_path = str(tmp_path / "results.xml")
        write_junit_xml(report, output_path)

        content = Path(output_path).read_text()
        assert '<?xml version="1.0"' in content
        assert "kintsugi-stress" in content
        assert 'name="j-1"' in content
        assert "<failure" in content  # hollow
        assert "<error" in content  # error
        assert "<skipped" in content  # untested
