"""Tests for the metrics engine (integration tests)."""

import os
import tempfile
import json

import pytest

from terrarium.metrics.engine import MetricsEngine
from terrarium.ecosystem.model import build_ecosystem


class TestMetricsEngine:
    """Integration tests for the metrics engine."""

    def test_scan_empty_dir(self):
        """Scanning an empty directory returns empty metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert len(project.modules) == 0

    def test_scan_with_python_files(self):
        """Scanning finds Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")
            with open(os.path.join(tmpdir, "utils.py"), "w") as f:
                f.write("def add(a, b):\n    return a + b\n")

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert "main.py" in project.modules
            assert "utils.py" in project.modules

    def test_scan_with_coverage(self):
        """Scanning ingests coverage data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            coverage = {
                "files": {
                    "main.py": {"summary": {"covered_lines": 3, "num_statements": 5}},
                }
            }
            with open(os.path.join(tmpdir, "coverage.json"), "w") as f:
                json.dump(coverage, f)

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert project.modules["main.py"].test_coverage > 0

    def test_scan_complexity(self):
        """Scanning computes complexity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "complex.py"), "w") as f:
                f.write("def f(x):\n    if x:\n        for i in range(x):\n            if i > 5:\n                pass\n")

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert project.modules["complex.py"].complexity > 0

    def test_scan_role_detection(self):
        """Scanning detects module roles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Entry point
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")
            # Config
            with open(os.path.join(tmpdir, "config.py"), "w") as f:
                f.write("DEBUG = True\n")
            # Test
            test_dir = os.path.join(tmpdir, "tests")
            os.makedirs(test_dir)
            with open(os.path.join(test_dir, "test_main.py"), "w") as f:
                f.write("def test_main():\n    assert True\n")

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert project.modules["main.py"].is_entry_point is True
            assert project.modules["config.py"].is_config is True
            test_path = os.path.join("tests", "test_main.py")
            assert project.modules[test_path].is_test is True

    def test_analyze_file(self):
        """Analyze a specific file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "module.py")
            with open(filepath, "w") as f:
                f.write("def func():\n    pass\n")

            engine = MetricsEngine(tmpdir)
            metrics = engine.analyze_file(filepath)
            assert metrics.path == "module.py"
            assert metrics.complexity >= 0

    def test_scan_skip_hidden_dirs(self):
        """Hidden directories are skipped during scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hidden = os.path.join(tmpdir, ".hidden")
            os.makedirs(hidden)
            with open(os.path.join(hidden, "test.py"), "w") as f:
                f.write("x = 1\n")

            with open(os.path.join(tmpdir, "visible.py"), "w") as f:
                f.write("y = 2\n")

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            assert "visible.py" in project.modules
            hidden_path = os.path.join(".hidden", "test.py")
            assert hidden_path not in project.modules

    def test_scan_to_ecosystem(self):
        """Full pipeline: scan -> ecosystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")
            with open(os.path.join(tmpdir, "utils.py"), "w") as f:
                f.write("def add(a, b):\n    return a + b\n")

            engine = MetricsEngine(tmpdir)
            project = engine.scan()
            ecosystem = build_ecosystem(project)

            assert len(ecosystem.organisms) >= 2
            assert ecosystem.overall_health > 0
