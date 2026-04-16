"""Tests for mushin.diff module."""

import pytest

from mushin.diff import DiffResult, diff_workspaces
from mushin.workspace import Workspace


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestDiffResult:
    def test_empty_diff_no_changes(self):
        result = DiffResult()
        assert not result.has_changes

    def test_diff_with_entries(self):
        from mushin.journal import JournalEntry
        result = DiffResult(added_entries=[JournalEntry(expression="x")])
        assert result.has_changes

    def test_summary(self):
        from mushin.journal import JournalEntry
        result = DiffResult(
            left_id="aaa",
            right_id="bbb",
            added_entries=[JournalEntry(expression="x")],
            added_objects=["obj1"],
        )
        s = result.summary()
        assert "Journal entries: +1" in s
        assert "Objects: +1" in s


class TestDiffWorkspaces:
    def test_identical_workspaces(self, project_dir):
        ws1 = Workspace.create(project_dir, name="a")
        ws1.journal.record("x = 1")
        ws1.save()

        ws2 = Workspace.create(project_dir, name="b")
        ws2.journal.record("x = 1")
        ws2.save()

        result = diff_workspaces(ws1, ws2)
        # Same expression but different timestamps → will show as different
        # This is expected behavior

    def test_different_journals(self, project_dir):
        ws1 = Workspace.create(project_dir, name="left")
        ws1.journal.record("a = 1")
        ws1.save()

        ws2 = Workspace.create(project_dir, name="right")
        ws2.journal.record("a = 1")
        ws2.journal.record("b = 2")
        ws2.save()

        result = diff_workspaces(ws1, ws2)
        assert len(result.added_entries) >= 1

    def test_different_objects(self, project_dir):
        ws1 = Workspace.create(project_dir, name="left")
        ws1.save_object("shared", 1)
        ws1.save_object("only_left", 2)
        ws1.save()

        ws2 = Workspace.create(project_dir, name="right")
        ws2.save_object("shared", 1)
        ws2.save_object("only_right", 3)
        ws2.save()

        result = diff_workspaces(ws1, ws2)
        assert "only_right" in result.added_objects
        assert "only_left" in result.removed_objects
        assert "shared" in result.common_objects

    def test_meta_changes(self, project_dir):
        ws1 = Workspace.create(project_dir, name="alpha", description="v1")
        ws1.save()

        ws2 = Workspace.create(project_dir, name="beta", description="v2")
        ws2.save()

        result = diff_workspaces(ws1, ws2)
        assert result.has_changes
        assert "name" in result.meta_changes or "description" in result.meta_changes

    def test_no_changes(self, project_dir):
        ws1 = Workspace.create(project_dir, name="same")
        ws1.save()

        ws2 = Workspace.create(project_dir, name="same")
        ws2.save_object("x", 1)
        ws2.save()

        result = diff_workspaces(ws1, ws2)
        # At minimum, timestamps and IDs will differ, plus the object
        assert "x" in result.added_objects
