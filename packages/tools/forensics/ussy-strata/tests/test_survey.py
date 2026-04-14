"""Tests for the survey module (stratagit.core.survey)."""

import pytest
from stratagit.core.survey import survey, format_report
from stratagit.core import GeologicalReport


class TestSurvey:
    def test_basic_survey(self, git_repo):
        report = survey(git_repo)
        assert isinstance(report, GeologicalReport)
        assert report.total_strata > 0

    def test_survey_repo_path(self, git_repo):
        report = survey(git_repo)
        assert report.repo_path

    def test_survey_has_minerals(self, git_repo):
        report = survey(git_repo)
        assert isinstance(report.mineral_composition, dict)
        # Should have some minerals from the .py and .js files
        if report.mineral_composition:
            assert len(report.mineral_composition) > 0

    def test_survey_has_stability(self, git_repo):
        report = survey(git_repo)
        assert isinstance(report.stability_breakdown, dict)

    def test_survey_max_commits(self, git_repo):
        report = survey(git_repo, max_commits=1)
        assert report.total_strata <= 1

    def test_survey_without_fossils(self, git_repo):
        report = survey(git_repo, include_fossils=False)
        assert report.fossil_count == 0

    def test_survey_without_unconformities(self, git_repo):
        report = survey(git_repo, include_unconformities=False)
        assert report.unconformity_count == 0

    def test_survey_without_faults(self, git_repo):
        report = survey(git_repo, include_faults=False)
        assert report.fault_count == 0

    def test_survey_rich_repo(self, rich_repo):
        report = survey(rich_repo)
        assert report.total_strata >= 5  # at least 5 commits
        assert report.total_intrusions >= 0

    def test_survey_age(self, git_repo):
        report = survey(git_repo)
        assert report.age_days >= 0

    def test_empty_repo(self, tmp_path):
        import subprocess
        repo = tmp_path / "empty"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=str(repo), capture_output=True)
        report = survey(str(repo))
        assert report.total_strata == 0


class TestFormatReport:
    def test_format_basic(self, git_repo):
        report = survey(git_repo)
        output = format_report(report)
        assert "STRATAGIT" in output
        assert "GEOLOGICAL" in output

    def test_format_contains_overview(self, git_repo):
        report = survey(git_repo)
        output = format_report(report)
        assert "Total strata" in output

    def test_format_empty_report(self):
        report = GeologicalReport()
        output = format_report(report)
        assert "STRATAGIT" in output

    def test_format_contains_minerals(self, git_repo):
        report = survey(git_repo)
        output = format_report(report)
        if report.mineral_composition:
            assert "MINERAL COMPOSITION" in output
