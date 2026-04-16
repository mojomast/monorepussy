"""Tests for mushin.objects module."""

import pytest

from mushin.objects import ObjectCache


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestObjectCache:
    def test_put_and_get(self, project_dir):
        cache = ObjectCache(project_dir, "ws-001")
        cache.put("num", 42)
        assert cache.get("num") == 42

    def test_put_dict(self, project_dir):
        cache = ObjectCache(project_dir, "ws-002")
        data = {"name": "test", "values": [1, 2, 3]}
        cache.put("data", data)
        assert cache.get("data") == data

    def test_put_list(self, project_dir):
        cache = ObjectCache(project_dir, "ws-003")
        cache.put("items", [1, "two", 3.0])
        assert cache.get("items") == [1, "two", 3.0]

    def test_has(self, project_dir):
        cache = ObjectCache(project_dir, "ws-004")
        assert not cache.has("x")
        cache.put("x", 1)
        assert cache.has("x")

    def test_keys(self, project_dir):
        cache = ObjectCache(project_dir, "ws-005")
        cache.put("a", 1)
        cache.put("b", 2)
        assert sorted(cache.keys()) == ["a", "b"]

    def test_delete(self, project_dir):
        cache = ObjectCache(project_dir, "ws-006")
        cache.put("temp", "val")
        assert cache.delete("temp") is True
        assert not cache.has("temp")

    def test_delete_missing(self, project_dir):
        cache = ObjectCache(project_dir, "ws-007")
        assert cache.delete("nope") is False

    def test_get_missing(self, project_dir):
        cache = ObjectCache(project_dir, "ws-008")
        with pytest.raises(KeyError):
            cache.get("nonexistent")

    def test_clear(self, project_dir):
        cache = ObjectCache(project_dir, "ws-009")
        cache.put("a", 1)
        cache.put("b", 2)
        count = cache.clear()
        assert count == 2
        assert cache.keys() == []

    def test_overwrite(self, project_dir):
        cache = ObjectCache(project_dir, "ws-010")
        cache.put("val", 1)
        cache.put("val", 2)
        assert cache.get("val") == 2

    def test_complex_object(self, project_dir):
        cache = ObjectCache(project_dir, "ws-011")
        import datetime as dt
        obj = {
            "date": dt.date(2025, 1, 1),
            "nested": {"a": [1, 2, 3]},
        }
        cache.put("complex", obj)
        assert cache.get("complex") == obj

    def test_empty_keys(self, project_dir):
        cache = ObjectCache(project_dir, "ws-012")
        assert cache.keys() == []
