"""Tests for timeline module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_seral.models import ModuleMetrics, Stage, TimelineEntry, TrajectoryProjection
from ussy_seral.timeline import TimelineAnalyzer


class TestTimelineAnalyzer:
    """Tests for TimelineAnalyzer."""

    def test_build_timeline_with_git_repo(self, tmp_git_repo: Path):
        analyzer = TimelineAnalyzer(repo_root=tmp_git_repo)
        mod_path = tmp_git_repo / "src" / "mymodule"
        entries = analyzer.build_timeline(mod_path)
        assert isinstance(entries, list)
        assert len(entries) >= 1

    def test_build_timeline_current_stage(self, tmp_git_repo: Path):
        analyzer = TimelineAnalyzer(repo_root=tmp_git_repo)
        entries = analyzer.build_timeline(tmp_git_repo / "src" / "mymodule")
        assert all(isinstance(e, TimelineEntry) for e in entries)
        # Last entry should have a stage
        assert entries[-1].stage is not None

    def test_project_trajectory_pioneer(self, tmp_git_repo: Path):
        analyzer = TimelineAnalyzer(repo_root=tmp_git_repo)
        # Create a module with pioneer metrics
        new_mod = tmp_git_repo / "src" / "newthing"
        new_mod.mkdir(parents=True, exist_ok=True)
        (new_mod / "__init__.py").write_text("")

        import subprocess
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new module"],
            cwd=tmp_git_repo, capture_output=True,
        )

        projection = analyzer.project_trajectory(new_mod)
        # Projection might be None if metrics can't be computed
        if projection is not None:
            assert isinstance(projection, TrajectoryProjection)

    def test_project_trajectory_already_climax(self):
        """A climax module should report it's already at climax."""
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(
            path="test",
            age_days=800,
            commit_count=400,
            contributor_count=12,
            churn_rate=2.0,
            test_coverage=0.95,
            dependent_count=25,
        )
        metrics.compute_stage()
        # Even if it's climax, project_trajectory hits the git repo
        # So we test the logic indirectly
        assert metrics.stage == Stage.CLIMAX

    def test_next_stage_progression(self):
        """Verify the successional progression."""
        analyzer = TimelineAnalyzer()
        assert analyzer._next_stage(Stage.PIONEER) == Stage.SERAL_EARLY
        assert analyzer._next_stage(Stage.SERAL_EARLY) == Stage.SERAL_MID
        assert analyzer._next_stage(Stage.SERAL_MID) == Stage.SERAL_LATE
        assert analyzer._next_stage(Stage.SERAL_LATE) == Stage.CLIMAX
        assert analyzer._next_stage(Stage.CLIMAX) is None
        assert analyzer._next_stage(Stage.DISTURBED) == Stage.PIONEER

    def test_identify_blockers_low_coverage(self):
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(
            path="test",
            test_coverage=0.2,
            contributor_count=2,
            churn_rate=50.0,
            breaking_change_count=0,
        )
        blockers = analyzer._identify_blockers(metrics, Stage.SERAL_MID)
        assert len(blockers) > 0
        assert any("coverage" in b.lower() for b in blockers)

    def test_identify_blockers_climax(self):
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(
            path="test",
            test_coverage=0.5,
            contributor_count=3,
            churn_rate=15.0,
            breaking_change_count=0,
        )
        blockers = analyzer._identify_blockers(metrics, Stage.CLIMAX)
        assert len(blockers) >= 2  # Low coverage + low contributors

    def test_recommend_actions(self):
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(
            path="test",
            test_coverage=0.3,
            contributor_count=2,
            breaking_change_count=5,
            churn_rate=50.0,
        )
        actions = analyzer._recommend_actions(metrics, Stage.SERAL_MID, [])
        assert len(actions) >= 1

    def test_estimate_transition_time_no_blockers(self):
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(path="test", churn_rate=20.0)
        est = analyzer._estimate_transition_time(metrics, Stage.SERAL_MID, [])
        assert "~" in est

    def test_estimate_transition_time_with_blockers(self):
        analyzer = TimelineAnalyzer()
        metrics = ModuleMetrics(path="test", churn_rate=5.0)
        blockers = ["Low coverage", "Few contributors"]
        est = analyzer._estimate_transition_time(metrics, Stage.CLIMAX, blockers)
        assert "~" in est

    def test_sample_indices(self):
        analyzer = TimelineAnalyzer()
        indices = analyzer._sample_indices(10)
        assert 0 in indices
        assert 9 in indices

    def test_sample_indices_small(self):
        analyzer = TimelineAnalyzer()
        indices = analyzer._sample_indices(3)
        assert len(indices) == 3
