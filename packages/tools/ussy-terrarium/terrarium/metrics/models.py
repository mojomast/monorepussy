"""Data structures for code metrics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ModuleMetrics:
    """Health metrics for a single module (file)."""

    path: str
    churn_rate: float = 0.0
    complexity: int = 0
    test_coverage: float = 0.0
    bug_count: int = 0
    dependency_count: int = 0
    lines_of_code: int = 0
    commit_count: int = 0
    age_days: int = 0
    days_since_last_change: int = 0
    is_dead: bool = False
    is_entry_point: bool = False
    is_test: bool = False
    is_generated: bool = False
    is_deprecated: bool = False
    is_config: bool = False
    functions: List[Dict] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def module_role(self) -> str:
        """Determine the role of this module."""
        if self.is_deprecated:
            return "deprecated"
        if self.is_entry_point:
            return "entry_point"
        if self.is_test:
            return "test"
        if self.is_generated:
            return "generated"
        if self.is_config:
            return "config"
        return "library"


@dataclass
class ProjectMetrics:
    """Aggregate metrics for an entire project."""

    root_path: str
    modules: Dict[str, ModuleMetrics] = field(default_factory=dict)
    total_lines: int = 0
    total_commits: int = 0
    avg_churn: float = 0.0
    avg_complexity: float = 0.0
    avg_coverage: float = 0.0

    def compute_aggregates(self) -> None:
        """Compute aggregate metrics from module data."""
        if not self.modules:
            return
        self.total_lines = sum(m.lines_of_code for m in self.modules.values())
        self.total_commits = sum(m.commit_count for m in self.modules.values())
        self.avg_churn = sum(m.churn_rate for m in self.modules.values()) / len(self.modules)
        self.avg_complexity = sum(m.complexity for m in self.modules.values()) / len(self.modules)
        modules_with_coverage = [m for m in self.modules.values() if m.test_coverage > 0]
        if modules_with_coverage:
            self.avg_coverage = sum(m.test_coverage for m in modules_with_coverage) / len(modules_with_coverage)
