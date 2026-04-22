"""Timeline — successional trajectory analysis and projection."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ussy_seral.git_utils import (
    get_churn_rate,
    get_commit_count,
    get_contributor_count,
    get_module_age_days,
    get_test_coverage,
    get_weekly_commit_history,
    get_contributor_history,
)
from ussy_seral.models import (
    ModuleMetrics,
    Stage,
    TimelineEntry,
    TrajectoryProjection,
)


class TimelineAnalyzer:
    """Analyzes successional trajectory for a module."""

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    def build_timeline(self, module_path: str | Path) -> list[TimelineEntry]:
        """Build a timeline of stage transitions for a module."""
        module_path = Path(module_path)
        entries: list[TimelineEntry] = []

        # Analyze historical data at intervals
        commit_history = get_weekly_commit_history(module_path, self.repo_root)
        if not commit_history:
            # Create a single entry from current state
            metrics = self._get_current_metrics(module_path)
            entries.append(TimelineEntry(
                stage=metrics.stage or Stage.PIONEER,
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                metrics=metrics,
            ))
            return entries

        # Build timeline from commit history
        total_weeks = len(commit_history)
        if total_weeks <= 1:
            metrics = self._get_current_metrics(module_path)
            entries.append(TimelineEntry(
                stage=metrics.stage or Stage.PIONEER,
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                metrics=metrics,
            ))
            return entries

        # Sample at key intervals
        sample_indices = self._sample_indices(total_weeks)
        for idx in sample_indices:
            week_data = commit_history[idx]
            age_days = (total_weeks - idx) * 7
            commits_so_far = sum(c["commits"] for c in commit_history[: idx + 1])

            # Estimate metrics at this point
            estimated_metrics = ModuleMetrics(
                path=str(module_path),
                age_days=float(age_days),
                commit_count=commits_so_far,
                contributor_count=max(1, commits_so_far // 10),
                churn_rate=float(week_data["commits"]) * 5,  # rough estimate
                test_coverage=min(commits_so_far / 100, 0.95),
            )
            estimated_metrics.compute_stage()

            entries.append(TimelineEntry(
                stage=estimated_metrics.stage or Stage.PIONEER,
                date=week_data["week"],
                metrics=estimated_metrics,
            ))

        # Add current state
        current_metrics = self._get_current_metrics(module_path)
        entries.append(TimelineEntry(
            stage=current_metrics.stage or Stage.PIONEER,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            metrics=current_metrics,
        ))

        return entries

    def project_trajectory(self, module_path: str | Path) -> Optional[TrajectoryProjection]:
        """Project the future trajectory of a module."""
        module_path = Path(module_path)
        metrics = self._get_current_metrics(module_path)
        if metrics.stage is None:
            metrics.compute_stage()

        current_stage = metrics.stage
        if current_stage is None:
            return None

        # If already climax, no projection needed
        if current_stage == Stage.CLIMAX:
            return TrajectoryProjection(
                target_stage=Stage.CLIMAX,
                estimated_time="Already at climax",
                blockers=[],
                recommended_actions=[],
            )

        # If disturbed, uncertain trajectory
        if current_stage == Stage.DISTURBED:
            return TrajectoryProjection(
                target_stage=Stage.PIONEER,
                estimated_time="Unknown — disturbance in progress",
                blockers=["Module is in disturbed state"],
                recommended_actions=[
                    "Stabilize the disturbance before projecting trajectory",
                    "Focus on re-establishing module boundaries",
                ],
            )

        # Determine next stage
        next_stage = self._next_stage(current_stage)
        if next_stage is None:
            return None

        # Estimate time to next stage
        blockers = self._identify_blockers(metrics, next_stage)
        recommended_actions = self._recommend_actions(metrics, next_stage, blockers)
        estimated_time = self._estimate_transition_time(metrics, next_stage, blockers)

        return TrajectoryProjection(
            target_stage=next_stage,
            estimated_time=estimated_time,
            blockers=blockers,
            recommended_actions=recommended_actions,
        )

    def _get_current_metrics(self, module_path: Path) -> ModuleMetrics:
        """Get current metrics for a module."""
        metrics = ModuleMetrics(
            path=str(module_path),
            age_days=get_module_age_days(module_path, self.repo_root),
            commit_count=get_commit_count(module_path, self.repo_root),
            contributor_count=get_contributor_count(module_path, self.repo_root),
            churn_rate=get_churn_rate(module_path, self.repo_root),
            test_coverage=get_test_coverage(module_path, self.repo_root),
        )
        metrics.compute_stage()
        return metrics

    def _sample_indices(self, total: int) -> list[int]:
        """Sample indices at reasonable intervals."""
        if total <= 5:
            return list(range(total))
        # Sample at start, 25%, 50%, 75%
        return [
            0,
            total // 4,
            total // 2,
            3 * total // 4,
            total - 1,
        ]

    def _next_stage(self, current: Stage) -> Optional[Stage]:
        """Get the next successional stage."""
        progression = {
            Stage.PIONEER: Stage.SERAL_EARLY,
            Stage.SERAL_EARLY: Stage.SERAL_MID,
            Stage.SERAL_MID: Stage.SERAL_LATE,
            Stage.SERAL_LATE: Stage.CLIMAX,
            Stage.CLIMAX: None,
            Stage.DISTURBED: Stage.PIONEER,
        }
        return progression.get(current)

    def _identify_blockers(self, metrics: ModuleMetrics, target: Stage) -> list[str]:
        """Identify what's blocking transition to the target stage."""
        blockers = []

        if target.seral_tier >= Stage.SERAL_MID.seral_tier:
            if metrics.test_coverage < 0.5:
                blockers.append(
                    f"Test coverage at {metrics.test_coverage:.0%} (need 50%+)"
                )
            if metrics.contributor_count < 3:
                blockers.append(
                    f"Only {metrics.contributor_count} contributor(s) (target stage typically 3+)"
                )

        if target.seral_tier >= Stage.SERAL_LATE.seral_tier:
            if metrics.test_coverage < 0.7:
                blockers.append(
                    f"Test coverage at {metrics.test_coverage:.0%} (need 70%+)"
                )
            if metrics.breaking_change_count > 2:
                blockers.append(
                    f"API surface not stable ({metrics.breaking_change_count} breaking changes in last 60 days)"
                )

        if target == Stage.CLIMAX:
            if metrics.test_coverage < 0.8:
                blockers.append(
                    f"Test coverage at {metrics.test_coverage:.0%} (need 80%+)"
                )
            if metrics.contributor_count < 6:
                blockers.append(
                    f"Only {metrics.contributor_count} contributor(s) (climax typically 6+)"
                )
            if metrics.churn_rate > 10:
                blockers.append(
                    f"Churn rate still high ({metrics.churn_rate:.0f}/week, need <10)"
                )

        return blockers

    def _recommend_actions(
        self, metrics: ModuleMetrics, target: Stage, blockers: list[str]
    ) -> list[str]:
        """Recommend actions to accelerate succession."""
        actions = []

        if metrics.test_coverage < 0.5:
            actions.append("Increase test coverage to 50% — focus on happy paths first")
        elif metrics.test_coverage < 0.8:
            actions.append("Increase test coverage to 80% — focus on edge cases")

        if metrics.contributor_count < 6:
            actions.append("Document onboarding guide — attract more contributors")

        if metrics.breaking_change_count > 2:
            actions.append("Freeze public API — add deprecation path for unstable interfaces")

        if metrics.churn_rate > 10:
            actions.append("Reduce churn by stabilizing interfaces before adding features")

        if not actions and not blockers:
            actions.append("Module is on track — continue current practices")

        return actions[:4]  # Cap at 4 recommendations

    def _estimate_transition_time(
        self, metrics: ModuleMetrics, target: Stage, blockers: list[str]
    ) -> str:
        """Estimate time to transition to the target stage."""
        blocker_count = len(blockers)

        if blocker_count == 0:
            return "~1-2 months"

        # Base estimate on age and blocker count
        months_per_blocker = 2
        base_months = blocker_count * months_per_blocker

        # Adjust for current velocity
        if metrics.churn_rate > 20:
            base_months = max(base_months - 2, 1)

        low = max(base_months - 1, 1)
        high = base_months + 2

        return f"~{low}-{high} months"
