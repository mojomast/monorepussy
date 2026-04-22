"""Tests for the metrics models."""

import pytest

from terrarium.metrics.models import ModuleMetrics, ProjectMetrics


class TestModuleMetrics:
    """Tests for ModuleMetrics dataclass."""

    def test_default_values(self):
        """ModuleMetrics has sensible defaults."""
        m = ModuleMetrics(path="test.py")
        assert m.path == "test.py"
        assert m.churn_rate == 0.0
        assert m.complexity == 0
        assert m.test_coverage == 0.0
        assert m.bug_count == 0
        assert m.is_dead is False
        assert m.functions == []
        assert m.imports == []

    def test_module_role_library(self):
        """Default role is library."""
        m = ModuleMetrics(path="utils.py")
        assert m.module_role == "library"

    def test_module_role_entry_point(self):
        """Entry point detection."""
        m = ModuleMetrics(path="main.py", is_entry_point=True)
        assert m.module_role == "entry_point"

    def test_module_role_test(self):
        """Test file role."""
        m = ModuleMetrics(path="test_foo.py", is_test=True)
        assert m.module_role == "test"

    def test_module_role_deprecated(self):
        """Deprecated takes priority."""
        m = ModuleMetrics(path="old.py", is_deprecated=True, is_entry_point=True)
        assert m.module_role == "deprecated"

    def test_module_role_generated(self):
        """Generated file role."""
        m = ModuleMetrics(path="api_pb2.py", is_generated=True)
        assert m.module_role == "generated"

    def test_module_role_config(self):
        """Config file role."""
        m = ModuleMetrics(path="settings.py", is_config=True)
        assert m.module_role == "config"


class TestProjectMetrics:
    """Tests for ProjectMetrics dataclass."""

    def test_empty_project(self):
        """Empty project has zero aggregates."""
        p = ProjectMetrics(root_path="/tmp/test")
        assert p.total_lines == 0
        assert p.avg_churn == 0.0

    def test_compute_aggregates(self):
        """Aggregates are computed correctly."""
        p = ProjectMetrics(root_path="/tmp/test")
        p.modules = {
            "a.py": ModuleMetrics(path="a.py", lines_of_code=100, commit_count=5,
                                   churn_rate=2.0, complexity=10, test_coverage=0.8),
            "b.py": ModuleMetrics(path="b.py", lines_of_code=50, commit_count=3,
                                   churn_rate=1.0, complexity=5, test_coverage=0.6),
        }
        p.compute_aggregates()
        assert p.total_lines == 150
        assert p.total_commits == 8
        assert abs(p.avg_churn - 1.5) < 0.01
        assert abs(p.avg_complexity - 7.5) < 0.01

    def test_compute_aggregates_no_coverage(self):
        """Modules with 0 coverage don't affect average."""
        p = ProjectMetrics(root_path="/tmp/test")
        p.modules = {
            "a.py": ModuleMetrics(path="a.py", lines_of_code=100,
                                   churn_rate=2.0, complexity=10, test_coverage=0.8),
            "b.py": ModuleMetrics(path="b.py", lines_of_code=50,
                                   churn_rate=1.0, complexity=5, test_coverage=0.0),
        }
        p.compute_aggregates()
        assert abs(p.avg_coverage - 0.8) < 0.01
