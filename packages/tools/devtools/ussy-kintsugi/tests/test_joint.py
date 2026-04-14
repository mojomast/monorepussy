"""Tests for the Joint data model and JointStore."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kintsugi.joint import Joint, JointStore, KINTSUGI_DIR, JOINTS_FILE, _generate_joint_id


# ── Joint dataclass tests ──


class TestJointCreation:
    """Test Joint creation and defaults."""

    def test_joint_default_values(self):
        j = Joint()
        assert j.id != ""  # Auto-generated
        assert j.timestamp != ""  # Auto-generated
        assert j.severity == "warning"
        assert j.status == "solid_gold"
        assert j.line == 0
        assert j.file == ""

    def test_joint_with_explicit_values(self):
        j = Joint(
            id="j-20240315-proj892",
            file="src/auth/login.py",
            line=42,
            timestamp="2024-03-15T10:30:00+00:00",
            bug_ref="PROJ-892",
            severity="critical",
            break_description="user.email was None",
            repair_description="Added None guard",
            removal_impact="TypeError crash",
            test_ref="test_oauth_null_email",
            status="solid_gold",
        )
        assert j.id == "j-20240315-proj892"
        assert j.file == "src/auth/login.py"
        assert j.line == 42
        assert j.bug_ref == "PROJ-892"
        assert j.severity == "critical"

    def test_joint_auto_generates_id(self):
        j = Joint(bug_ref="PROJ-892", timestamp="2024-03-15T10:30:00+00:00")
        assert j.id == "j-20240315-proj892"

    def test_joint_auto_generates_timestamp(self):
        before = datetime.now(timezone.utc)
        j = Joint(bug_ref="TEST-1")
        after = datetime.now(timezone.utc)
        ts = datetime.fromisoformat(j.timestamp)
        assert before <= ts <= after

    def test_joint_post_init_does_not_override_explicit_id(self):
        j = Joint(id="my-custom-id", bug_ref="PROJ-1")
        assert j.id == "my-custom-id"

    def test_joint_post_init_does_not_override_explicit_timestamp(self):
        j = Joint(bug_ref="PROJ-1", timestamp="2024-01-01T00:00:00+00:00")
        assert j.timestamp == "2024-01-01T00:00:00+00:00"


class TestJointSerialization:
    """Test Joint serialization/deserialization."""

    def test_to_dict(self):
        j = Joint(
            id="j-20240315-proj892",
            file="src/auth/login.py",
            line=42,
            bug_ref="PROJ-892",
            severity="critical",
            break_description="null pointer",
            repair_description="added guard",
        )
        d = j.to_dict()
        assert d["id"] == "j-20240315-proj892"
        assert d["file"] == "src/auth/login.py"
        assert d["line"] == 42
        assert d["severity"] == "critical"

    def test_from_dict(self):
        data = {
            "id": "j-20240315-proj892",
            "file": "src/auth/login.py",
            "line": 42,
            "timestamp": "2024-03-15T10:30:00+00:00",
            "bug_ref": "PROJ-892",
            "severity": "critical",
            "break_description": "null pointer",
            "repair_description": "added guard",
            "removal_impact": "",
            "test_ref": "",
            "status": "solid_gold",
            "last_stress_tested": "",
        }
        j = Joint.from_dict(data)
        assert j.id == "j-20240315-proj892"
        assert j.file == "src/auth/login.py"

    def test_from_dict_ignores_unknown_fields(self):
        data = {
            "id": "j-test",
            "unknown_field": "should be ignored",
        }
        j = Joint.from_dict(data)
        assert j.id == "j-test"
        assert not hasattr(j, "unknown_field")

    def test_to_jsonl(self):
        j = Joint(id="j-test", bug_ref="X-1")
        jsonl = j.to_jsonl()
        parsed = json.loads(jsonl)
        assert parsed["id"] == "j-test"

    def test_roundtrip(self):
        j = Joint(
            id="j-20240315-proj892",
            file="src/auth/login.py",
            line=42,
            timestamp="2024-03-15T10:30:00+00:00",
            bug_ref="PROJ-892",
            severity="critical",
            break_description="null pointer",
            repair_description="added guard",
        )
        d = j.to_dict()
        j2 = Joint.from_dict(d)
        assert j2.id == j.id
        assert j2.file == j.file
        assert j2.line == j.line
        assert j2.bug_ref == j.bug_ref


class TestJointIdGeneration:
    """Test joint ID generation."""

    def test_generate_id(self):
        ts = datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc)
        jid = _generate_joint_id(ts, "PROJ-892")
        assert jid == "j-20240315-proj892"

    def test_generate_id_normalizes_bug_ref(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        jid = _generate_joint_id(ts, "PROJ-892-A")
        assert jid == "j-20240101-proj892a"

    def test_generate_id_lowercases(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        jid = _generate_joint_id(ts, "ABC")
        assert jid == "j-20240101-abc"


# ── JointStore tests ──


class TestJointStore:
    """Test JointStore CRUD operations."""

    @pytest.fixture
    def store(self, tmp_path):
        return JointStore(root=str(tmp_path))

    def test_load_all_empty(self, store):
        assert store.load_all() == []

    def test_save_and_load(self, store):
        j = Joint(id="j-test", file="test.py", line=1, bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j)
        loaded = store.load_all()
        assert len(loaded) == 1
        assert loaded[0].id == "j-test"

    def test_save_multiple(self, store):
        j1 = Joint(id="j-1", bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        j2 = Joint(id="j-2", bug_ref="X-2", timestamp="2024-01-02T00:00:00+00:00")
        store.save(j1)
        store.save(j2)
        loaded = store.load_all()
        assert len(loaded) == 2

    def test_update(self, store):
        j = Joint(id="j-test", bug_ref="X-1", severity="warning", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j)
        updated = store.update("j-test", severity="critical")
        assert updated is not None
        assert updated.severity == "critical"

    def test_update_nonexistent(self, store):
        result = store.update("nonexistent", severity="critical")
        assert result is None

    def test_delete(self, store):
        j = Joint(id="j-test", bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j)
        assert store.delete("j-test") is True
        assert store.load_all() == []

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False

    def test_find_by_file(self, store):
        j1 = Joint(id="j-1", file="a.py", bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        j2 = Joint(id="j-2", file="b.py", bug_ref="X-2", timestamp="2024-01-01T00:00:00+00:00")
        j3 = Joint(id="j-3", file="a.py", bug_ref="X-3", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j1)
        store.save(j2)
        store.save(j3)
        found = store.find_by_file("a.py")
        assert len(found) == 2

    def test_find_by_id(self, store):
        j = Joint(id="j-test", bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j)
        found = store.find_by_id("j-test")
        assert found is not None
        assert found.id == "j-test"

    def test_find_by_id_not_found(self, store):
        found = store.find_by_id("nonexistent")
        assert found is None

    def test_find_by_bug_ref(self, store):
        j1 = Joint(id="j-1", bug_ref="PROJ-892", timestamp="2024-01-01T00:00:00+00:00")
        j2 = Joint(id="j-2", bug_ref="PROJ-1203", timestamp="2024-01-01T00:00:00+00:00")
        j3 = Joint(id="j-3", bug_ref="PROJ-892", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j1)
        store.save(j2)
        store.save(j3)
        found = store.find_by_bug_ref("PROJ-892")
        assert len(found) == 2

    def test_find_hollow(self, store):
        j1 = Joint(id="j-1", bug_ref="X-1", status="solid_gold", timestamp="2024-01-01T00:00:00+00:00")
        j2 = Joint(id="j-2", bug_ref="X-2", status="hollow", timestamp="2024-01-01T00:00:00+00:00")
        j3 = Joint(id="j-3", bug_ref="X-3", status="hollow", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j1)
        store.save(j2)
        store.save(j3)
        hollow = store.find_hollow()
        assert len(hollow) == 2

    def test_save_all_overwrites(self, store):
        j1 = Joint(id="j-1", bug_ref="X-1", timestamp="2024-01-01T00:00:00+00:00")
        store.save(j1)
        j2 = Joint(id="j-2", bug_ref="X-2", timestamp="2024-01-01T00:00:00+00:00")
        store.save_all([j2])
        loaded = store.load_all()
        assert len(loaded) == 1
        assert loaded[0].id == "j-2"

    def test_corrupt_jsonl_line_skipped(self, store, tmp_path):
        """Corrupt lines in JSONL should be skipped gracefully."""
        store._ensure_dir()
        with open(store.path, "w") as f:
            f.write("not valid json\n")
            f.write('{"id":"j-good","file":"","line":0,"timestamp":"","bug_ref":"","severity":"warning","break_description":"","repair_description":"","removal_impact":"","test_ref":"","status":"solid_gold","last_stress_tested":""}\n')
        loaded = store.load_all()
        assert len(loaded) == 1
        assert loaded[0].id == "j-good"
