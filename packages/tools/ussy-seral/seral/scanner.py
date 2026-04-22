"""Scanner — classify modules into successional stages."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from seral.git_utils import (
    get_breaking_change_count,
    get_churn_rate,
    get_churn_spike,
    get_commit_count,
    get_contributor_count,
    get_contributor_spike,
    get_deletion_ratio,
    get_dependent_count,
    get_file_count,
    get_file_type_diversity,
    get_module_age_days,
    get_test_coverage,
    is_git_repo,
    find_repo_root,
)
from seral.models import ModuleMetrics, Stage, StageTransition


class Scanner:
    """Scans a repository and classifies modules into successional stages."""

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    def scan_module(self, module_path: str | Path) -> ModuleMetrics:
        """Collect metrics and classify a single module."""
        module_path = Path(module_path)
        repo = self.repo_root

        metrics = ModuleMetrics(
            path=str(module_path),
            age_days=get_module_age_days(module_path, repo),
            commit_count=get_commit_count(module_path, repo),
            contributor_count=get_contributor_count(module_path, repo),
            churn_rate=get_churn_rate(module_path, repo),
            test_coverage=get_test_coverage(module_path, repo),
            dependent_count=get_dependent_count(module_path, repo),
            file_count=get_file_count(module_path, repo),
            file_type_diversity=get_file_type_diversity(module_path, repo),
            deletion_ratio=get_deletion_ratio(module_path, repo),
            contributor_spike=get_contributor_spike(module_path, repo),
            churn_spike=get_churn_spike(module_path, repo),
            breaking_change_count=get_breaking_change_count(module_path, repo),
        )

        metrics.compute_stage()
        return metrics

    def scan_directory(self, directory: str | Path, depth: int = 2) -> list[ModuleMetrics]:
        """Scan all modules in a directory up to a given depth."""
        directory = Path(directory)
        results = []
        seen_dirs: set[str] = set()

        # Walk the directory tree and find module-like directories
        self._find_modules(directory, depth, results, seen_dirs)
        return results

    def _find_modules(
        self,
        directory: Path,
        depth: int,
        results: list[ModuleMetrics],
        seen_dirs: set[str],
        current_depth: int = 0,
    ) -> None:
        """Recursively find and scan module directories."""
        if current_depth > depth:
            return

        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.name.startswith(".") or entry.name == "__pycache__":
                continue
            if entry.is_dir() and str(entry) not in seen_dirs:
                seen_dirs.add(str(entry))
                # Check if this looks like a module (has source files)
                has_code = self._has_code_files(entry)
                if has_code:
                    try:
                        metrics = self.scan_module(entry)
                        results.append(metrics)
                    except Exception:
                        pass
                # Recurse into subdirectories
                self._find_modules(entry, depth, results, seen_dirs, current_depth + 1)

    def _has_code_files(self, directory: Path) -> bool:
        """Check if a directory contains code files."""
        code_extensions = {
            ".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".cpp", ".c",
            ".h", ".jsx", ".tsx", ".scala", ".kt", ".swift", ".sh",
        }
        try:
            for f in directory.rglob("*"):
                if f.is_file() and f.suffix in code_extensions:
                    return True
        except PermissionError:
            return False
        return False

    def record_transition(
        self,
        metrics: ModuleMetrics,
        previous_stage: Optional[Stage] = None,
        reason: str = "",
    ) -> Optional[StageTransition]:
        """Record a stage transition if the stage changed."""
        if previous_stage is None or metrics.stage is None:
            return None
        if previous_stage == metrics.stage:
            return None

        transition = StageTransition(
            path=metrics.path,
            from_stage=previous_stage,
            to_stage=metrics.stage,
            timestamp=datetime.now(timezone.utc),
            metrics=metrics,
            reason=reason,
        )
        return transition
