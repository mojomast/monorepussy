"""Disturbance detection — identify ecological reset events."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ussy_seral.git_utils import (
    get_churn_spike,
    get_contributor_spike,
    get_deletion_ratio,
    get_file_count,
    find_repo_root,
)
from ussy_seral.models import DisturbanceEvent, ModuleMetrics, Stage


class DisturbanceDetector:
    """Detects disturbance events in codebase modules."""

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    def detect(self, module_path: str | Path) -> list[DisturbanceEvent]:
        """Detect disturbance events for a module."""
        events: list[DisturbanceEvent] = []
        module_path = Path(module_path)

        # Check for major deletion
        deletion_ratio = get_deletion_ratio(module_path, self.repo_root)
        if deletion_ratio > 0.4:
            events.append(DisturbanceEvent(
                path=str(module_path),
                event_type="major_deletion",
                cause=f"Major deletion ({deletion_ratio:.0%} of files removed)",
                current_stage=Stage.DISTURBED,
                governance_shift="Strict → Experimental",
            ))

        # Check for contributor spike
        contributor_spike = get_contributor_spike(module_path, self.repo_root)
        if contributor_spike > 2.5:
            events.append(DisturbanceEvent(
                path=str(module_path),
                event_type="contributor_spike",
                cause=f"Contributor explosion (z-score: {contributor_spike:.1f})",
                current_stage=Stage.DISTURBED,
                governance_shift="Standard → Onboarding-heavy",
            ))

        # Check for churn spike
        churn_spike = get_churn_spike(module_path, self.repo_root)
        if churn_spike > 3.0:
            events.append(DisturbanceEvent(
                path=str(module_path),
                event_type="churn_spike",
                cause=f"Churn rate discontinuity (z-score: {churn_spike:.1f})",
                current_stage=Stage.DISTURBED,
                governance_shift="Stable → High-activity",
            ))

        return events

    def detect_all(self, modules: list[ModuleMetrics]) -> list[DisturbanceEvent]:
        """Detect disturbances across multiple modules."""
        all_events: list[DisturbanceEvent] = []
        for metrics in modules:
            if metrics.stage == Stage.DISTURBED:
                events = self.detect(metrics.path)
                # Set previous stage from metrics
                for event in events:
                    event.previous_stage = self._infer_previous_stage(metrics)
                all_events.extend(events)
        return all_events

    def _infer_previous_stage(self, metrics: ModuleMetrics) -> Stage:
        """Infer the previous stage before disturbance."""
        # Based on age and other metrics, guess what stage it was in before
        if metrics.age_days > 365:
            return Stage.CLIMAX
        elif metrics.age_days > 90:
            return Stage.SERAL_MID
        else:
            return Stage.PIONEER
