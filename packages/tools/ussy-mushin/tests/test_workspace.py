"""Tests for mushin.workspace module."""

import pickle
from pathlib import Path

import pytest

from mushin.workspace import (
    Workspace,
    WorkspaceMeta,
    delete_workspace,
    get_active_workspace_id,
    list_workspaces,
)


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestWorkspaceMeta:
    def test_auto_timestamps(self):
        meta = WorkspaceMeta(id="abc", name="test")
        assert meta.created_at
        assert meta.saved_at

    def test_to_dict_roundtrip(self):
        meta = WorkspaceMeta(
            id="abc",
            name="test",
            description="desc",
            parent_id="parent",
            branch_name="main",
            open_files=["a.py", "b.py"],
            environment={"PYTHON": "3.12"},
        )
        d = meta.to_dict()
        restored = WorkspaceMeta.from_dict(d)
        assert restored.id == "abc"
        assert restored.name == "test"
        assert restored.open_files == ["a.py", "b.py"]
        assert restored.environment == {"PYTHON": "3.12"}

    def test_from_dict_defaults(self):
        d = {"id": "x"}
        meta = WorkspaceMeta.from_dict(d)
        assert meta.name == ""
        assert meta.open_files == []


class TestWorkspace:
    def test_create(self, project_dir):
        ws = Workspace.create(project_dir, name="test-ws")
        assert ws.id
        assert ws.meta.name == "test-ws"

    def test_save_and_load(self, project_dir):
        ws = Workspace.create(project_dir, name="persist-test")
        ws.journal.record("hello", "world")
        ws.save()

        loaded = Workspace.load(project_dir, ws.id)
        assert loaded.meta.name == "persist-test"
        assert len(loaded.journal) == 1
        assert loaded.journal[0].expression == "hello"

    def test_save_object(self, project_dir):
        ws = Workspace.create(project_dir, name="obj-test")
        ws.save_object("mylist", [1, 2, 3])
        ws.save()

        loaded = Workspace.load(project_dir, ws.id)
        obj = loaded.load_object("mylist")
        assert obj == [1, 2, 3]

    def test_save_dict_object(self, project_dir):
        ws = Workspace.create(project_dir, name="dict-test")
        data = {"key": "value", "nested": {"a": 1}}
        ws.save_object("config", data)

        result = ws.load_object("config")
        assert result == data

    def test_list_objects(self, project_dir):
        ws = Workspace.create(project_dir, name="list-obj")
        ws.save_object("a", 1)
        ws.save_object("b", 2)
        assert sorted(ws.list_objects()) == ["a", "b"]

    def test_delete_object(self, project_dir):
        ws = Workspace.create(project_dir, name="del-obj")
        ws.save_object("temp", 42)
        ws.delete_object("temp")
        assert "temp" not in ws.list_objects()

    def test_load_missing_object(self, project_dir):
        ws = Workspace.create(project_dir, name="missing-obj")
        with pytest.raises(KeyError):
            ws.load_object("nonexistent")

    def test_set_active(self, project_dir):
        ws = Workspace.create(project_dir, name="active-test")
        ws.set_active()
        assert get_active_workspace_id(project_dir) == ws.id

    def test_repr(self, project_dir):
        ws = Workspace.create(project_dir, name="repr-test")
        r = repr(ws)
        assert "Workspace" in r
        assert "repr-test" in r


class TestListWorkspaces:
    def test_empty(self, project_dir):
        assert list_workspaces(project_dir) == []

    def test_multiple(self, project_dir):
        ws1 = Workspace.create(project_dir, name="ws1")
        ws1.save()
        ws2 = Workspace.create(project_dir, name="ws2")
        ws2.save()
        metas = list_workspaces(project_dir)
        assert len(metas) == 2
        names = {m.name for m in metas}
        assert "ws1" in names
        assert "ws2" in names


class TestDeleteWorkspace:
    def test_delete(self, project_dir):
        ws = Workspace.create(project_dir, name="to-delete")
        ws.save()
        delete_workspace(project_dir, ws.id)
        metas = list_workspaces(project_dir)
        assert all(m.id != ws.id for m in metas)

    def test_delete_nonexistent(self, project_dir):
        # Should not raise
        result = delete_workspace(project_dir, "nonexistent-id")
        assert result is True


class TestGetActiveWorkspaceId:
    def test_none_when_empty(self, project_dir):
        assert get_active_workspace_id(project_dir) is None

    def test_returns_active(self, project_dir):
        ws = Workspace.create(project_dir, name="active")
        ws.set_active()
        assert get_active_workspace_id(project_dir) == ws.id


class TestUnpicklableObjects:
    def test_unpicklable_stored_as_placeholder(self, project_dir):
        ws = Workspace.create(project_dir, name="unpicklable")
        # Use an object type that cannot be pickled: an open file handle
        import io
        fh = io.TextIOWrapper(io.BytesIO())
        ws.save_object("fh", fh)
        obj = ws.load_object("fh")
        # Should be the placeholder dict
        assert isinstance(obj, dict)
        assert obj.get("__mushin_unpicklable__") is True
