"""Main metrics engine — orchestrates all analysis modules."""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import ModuleMetrics, ProjectMetrics
from .git_churn import get_churn_for_file, get_all_file_churn
from .complexity import analyze_file_complexity, analyze_complexity
from .coverage import auto_detect_coverage
from .dead_code import scan_project_dead_code
from .stability import (
    classify_stability, classify_age, is_likely_dead,
    is_likely_generated, is_likely_config, is_likely_entry_point,
    is_likely_test, is_likely_deprecated,
)


class MetricsEngine:
    """Orchestrates code health analysis across multiple dimensions."""

    def __init__(self, root_path: str, since: Optional[str] = None) -> None:
        self.root_path = os.path.abspath(root_path)
        self.since = since

    def scan(self) -> ProjectMetrics:
        """Run a full metrics scan on the project.

        Returns:
            ProjectMetrics with all module data populated.
        """
        project = ProjectMetrics(root_path=self.root_path)

        # Collect Python files
        python_files = self._find_python_files()

        # Get churn data from git
        churn_data = get_all_file_churn(self.root_path, self.since)

        # Get coverage data
        coverage_data = auto_detect_coverage(self.root_path)

        # Get dead code analysis
        dead_code_data = scan_project_dead_code(self.root_path)

        for relpath in python_files:
            filepath = os.path.join(self.root_path, relpath)
            metrics = self._analyze_module(filepath, relpath, churn_data, coverage_data, dead_code_data)
            project.modules[relpath] = metrics

        project.compute_aggregates()
        return project

    def analyze_file(self, filepath: str) -> ModuleMetrics:
        """Analyze a single file in detail.

        Args:
            filepath: Absolute or relative path to the file.

        Returns:
            ModuleMetrics for the file.
        """
        if not os.path.isabs(filepath):
            filepath = os.path.join(self.root_path, filepath)
        relpath = os.path.relpath(filepath, self.root_path)

        churn_data = get_all_file_churn(self.root_path, self.since)
        coverage_data = auto_detect_coverage(self.root_path)
        dead_code_data = scan_project_dead_code(self.root_path)

        return self._analyze_module(filepath, relpath, churn_data, coverage_data, dead_code_data)

    def _find_python_files(self) -> List[str]:
        """Find all Python files in the project."""
        files = []
        skip_dirs = {".git", "__pycache__", "node_modules", ".tox", ".mypy_cache", ".pytest_cache", "venv", ".venv"}
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
            for f in filenames:
                if f.endswith(".py"):
                    relpath = os.path.relpath(os.path.join(dirpath, f), self.root_path)
                    files.append(relpath)
        return sorted(files)

    def _analyze_module(
        self,
        filepath: str,
        relpath: str,
        churn_data: Dict,
        coverage_data: Dict,
        dead_code_data: Dict,
    ) -> ModuleMetrics:
        """Analyze a single module, combining all metric sources."""
        metrics = ModuleMetrics(path=relpath)

        # Read source
        source = None
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            metrics.lines_of_code = sum(1 for line in source.split("\n") if line.strip())
        except OSError:
            pass

        # Churn from git
        if relpath in churn_data:
            churn_rate, commit_count, age_days, days_since = churn_data[relpath]
            metrics.churn_rate = churn_rate
            metrics.commit_count = commit_count
            metrics.age_days = age_days
            metrics.days_since_last_change = days_since
        else:
            # Try direct file analysis
            try:
                churn_rate, commit_count, age_days, days_since = get_churn_for_file(filepath, self.since)
                metrics.churn_rate = churn_rate
                metrics.commit_count = commit_count
                metrics.age_days = age_days
                metrics.days_since_last_change = days_since
            except Exception:
                pass

        # Complexity
        if filepath.endswith(".py"):
            total_complexity, functions = analyze_file_complexity(filepath)
            metrics.complexity = total_complexity
            metrics.functions = functions

        # Coverage
        for cov_path, cov_value in coverage_data.items():
            # Try matching by filename
            if relpath.endswith(cov_path) or cov_path.endswith(relpath):
                metrics.test_coverage = cov_value
                break

        # Role detection
        metrics.is_entry_point = is_likely_entry_point(relpath)
        metrics.is_test = is_likely_test(relpath)
        metrics.is_generated = is_likely_generated(relpath)
        metrics.is_config = is_likely_config(relpath)
        metrics.is_deprecated = is_likely_deprecated(relpath, source)

        # Dead code detection
        metrics.is_dead = is_likely_dead(
            metrics.days_since_last_change,
            metrics.is_deprecated
        )
        if relpath in dead_code_data:
            metrics.dependency_count = len(dead_code_data[relpath])

        # Count imports for dependency info
        if source:
            try:
                from .dead_code import ImportCollector
                import ast
                tree = ast.parse(source)
                ic = ImportCollector()
                ic.visit(tree)
                metrics.imports = ic.imports[:]
                for module, names in ic.from_imports.items():
                    metrics.imports.append(module)
                metrics.dependency_count = len(metrics.imports)
            except SyntaxError:
                pass

        return metrics
