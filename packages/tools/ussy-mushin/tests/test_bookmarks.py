"""Tests for mushin.bookmarks module."""

import pytest

from ussy_mushin.bookmarks import Bookmark, BookmarkManager


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestBookmark:
    def test_creation(self):
        bm = Bookmark(name="auth-flow", file_path="auth.py", line=42, annotation="Login handler")
        assert bm.name == "auth-flow"
        assert bm.file_path == "auth.py"
        assert bm.line == 42
        assert bm.created_at  # auto-generated

    def test_to_dict_roundtrip(self):
        bm = Bookmark(
            name="test",
            file_path="a.py",
            line=10,
            column=5,
            scroll_position=100,
            visible_range=(1, 50),
            annotation="note",
            tags=["important", "review"],
        )
        d = bm.to_dict()
        restored = Bookmark.from_dict(d)
        assert restored.name == "test"
        assert restored.visible_range == (1, 50)
        assert restored.tags == ["important", "review"]

    def test_from_dict_defaults(self):
        d = {"name": "x"}
        bm = Bookmark.from_dict(d)
        assert bm.file_path == ""
        assert bm.line == 0
        assert bm.tags == []


class TestBookmarkManager:
    def test_add_bookmark(self, project_dir):
        mgr = BookmarkManager(project_dir)
        bm = mgr.add(name="start", file_path="main.py", line=1)
        assert bm.name == "start"
        assert bm.file_path == "main.py"

    def test_get_bookmark(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="test", file_path="a.py")
        bm = mgr.get("test")
        assert bm is not None
        assert bm.file_path == "a.py"

    def test_get_missing(self, project_dir):
        mgr = BookmarkManager(project_dir)
        assert mgr.get("nope") is None

    def test_duplicate_name(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="dup", file_path="a.py")
        with pytest.raises(ValueError, match="already exists"):
            mgr.add(name="dup", file_path="b.py")

    def test_list_bookmarks(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="b1", file_path="a.py", workspace_id="ws1")
        mgr.add(name="b2", file_path="b.py", workspace_id="ws1")
        mgr.add(name="b3", file_path="c.py", workspace_id="ws2")
        assert len(mgr.list_bookmarks()) == 3
        assert len(mgr.list_bookmarks(workspace_id="ws1")) == 2
        assert len(mgr.list_bookmarks(workspace_id="ws2")) == 1

    def test_filter_by_tag(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="b1", tags=["important", "review"])
        mgr.add(name="b2", tags=["important"])
        mgr.add(name="b3", tags=["draft"])
        assert len(mgr.list_bookmarks(tag="important")) == 2
        assert len(mgr.list_bookmarks(tag="review")) == 1

    def test_delete_bookmark(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="temp", file_path="x.py")
        assert mgr.delete("temp") is True
        assert mgr.get("temp") is None

    def test_delete_missing(self, project_dir):
        mgr = BookmarkManager(project_dir)
        assert mgr.delete("nope") is False

    def test_update_bookmark(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="upd", file_path="a.py", line=1)
        bm = mgr.update("upd", line=50, annotation="moved")
        assert bm.line == 50
        assert bm.annotation == "moved"

    def test_update_missing(self, project_dir):
        mgr = BookmarkManager(project_dir)
        assert mgr.update("nope", line=10) is None

    def test_search_bookmarks(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="auth", file_path="auth.py", annotation="login flow")
        mgr.add(name="db", file_path="db.py", annotation="database setup")
        results = mgr.search("auth")
        assert len(results) == 1
        assert results[0].name == "auth"

    def test_search_case_insensitive(self, project_dir):
        mgr = BookmarkManager(project_dir)
        mgr.add(name="Test", file_path="A.py")
        results = mgr.search("test")
        assert len(results) == 1

    def test_persistence(self, project_dir):
        mgr1 = BookmarkManager(project_dir)
        mgr1.add(name="persist", file_path="x.py", line=10)

        mgr2 = BookmarkManager(project_dir)
        bm = mgr2.get("persist")
        assert bm is not None
        assert bm.line == 10

    def test_bookmark_with_full_context(self, project_dir):
        mgr = BookmarkManager(project_dir)
        bm = mgr.add(
            name="deep-dive",
            file_path="core/engine.py",
            line=234,
            column=15,
            scroll_position=200,
            visible_range=(210, 260),
            annotation="Understanding the dispatch loop",
            tags=["understanding", "loop"],
        )
        assert bm.visible_range == (210, 260)
        assert "understanding" in bm.tags
