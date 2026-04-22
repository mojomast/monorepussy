"""Tests for mushin.branching module."""

import pytest

from ussy_mushin.branching import Branch, BranchManager
from ussy_mushin.workspace import Workspace, get_active_workspace_id


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestBranch:
    def test_creation(self):
        b = Branch(name="experiment", workspace_id="ws1", parent_id="ws0")
        assert b.name == "experiment"
        assert b.workspace_id == "ws1"
        assert b.created_at  # auto-generated

    def test_to_dict_roundtrip(self):
        b = Branch(name="exp", workspace_id="ws1", parent_id="ws0", description="test branch")
        d = b.to_dict()
        restored = Branch.from_dict(d)
        assert restored.name == "exp"
        assert restored.description == "test branch"

    def test_from_dict_defaults(self):
        d = {"name": "x"}
        b = Branch.from_dict(d)
        assert b.workspace_id == ""
        assert b.description == ""


class TestBranchManager:
    def test_create_branch(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.journal.record("x = 1", "1")
        ws.save()

        mgr = BranchManager(project_dir)
        child = mgr.create_branch("experiment", ws.id)
        assert child.meta.parent_id == ws.id
        assert child.meta.branch_name == "experiment"

    def test_branch_inherits_journal(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.journal.record("a = 1")
        ws.journal.record("b = 2")
        ws.save()

        mgr = BranchManager(project_dir)
        child = mgr.create_branch("fork", ws.id)
        assert len(child.journal) == 2

    def test_branch_inherits_objects(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save_object("data", [1, 2, 3])
        ws.save()

        mgr = BranchManager(project_dir)
        child = mgr.create_branch("fork", ws.id)
        assert "data" in child.list_objects()
        obj = child.load_object("data")
        assert obj == [1, 2, 3]

    def test_branch_diverges(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.journal.record("x = 1")
        ws.save()

        mgr = BranchManager(project_dir)
        child = mgr.create_branch("fork", ws.id)

        # Record in child — should not affect parent
        child.journal.record("y = 2")
        child.save()

        parent_reloaded = Workspace.load(project_dir, ws.id)
        assert len(parent_reloaded.journal) == 1
        assert len(child.journal) == 2

    def test_list_branches(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        mgr.create_branch("b1", ws.id)
        mgr.create_branch("b2", ws.id)
        branches = mgr.list_branches()
        assert len(branches) == 2
        names = {b.name for b in branches}
        assert names == {"b1", "b2"}

    def test_duplicate_branch_name(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        mgr.create_branch("exp", ws.id)
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_branch("exp", ws.id)

    def test_delete_branch(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        mgr.create_branch("temp", ws.id)
        assert mgr.delete_branch("temp") is True
        assert mgr.get_branch("temp") is None

    def test_delete_nonexistent_branch(self, project_dir):
        mgr = BranchManager(project_dir)
        assert mgr.delete_branch("nope") is False

    def test_rename_branch(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        mgr.create_branch("old", ws.id)
        assert mgr.rename_branch("old", "new") is True
        assert mgr.get_branch("new") is not None
        assert mgr.get_branch("old") is None

    def test_rename_to_existing(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        mgr.create_branch("a", ws.id)
        mgr.create_branch("b", ws.id)
        with pytest.raises(ValueError, match="already exists"):
            mgr.rename_branch("a", "b")

    def test_get_workspace_for_branch(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr = BranchManager(project_dir)
        child = mgr.create_branch("exp", ws.id)

        loaded = mgr.get_workspace_for_branch("exp")
        assert loaded is not None
        assert loaded.id == child.id

    def test_get_workspace_for_missing_branch(self, project_dir):
        mgr = BranchManager(project_dir)
        assert mgr.get_workspace_for_branch("nope") is None

    def test_branch_persistence(self, project_dir):
        ws = Workspace.create(project_dir, name="parent")
        ws.save()

        mgr1 = BranchManager(project_dir)
        mgr1.create_branch("persist-test", ws.id)

        mgr2 = BranchManager(project_dir)
        assert mgr2.get_branch("persist-test") is not None
