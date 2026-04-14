"""Tests for the scar map module."""

import pytest

from kintsugi.joint import Joint
from kintsugi.scar_map import (
    FileScarInfo,
    DirectoryScarInfo,
    build_scar_map,
    group_by_directory,
    format_scar_map,
    find_hotspots,
)


def _make_joint(file="src/auth/login.py", severity="critical", status="solid_gold", bug_ref="X-1"):
    return Joint(
        id=f"j-test-{bug_ref}",
        file=file,
        line=1,
        timestamp="2024-01-01T00:00:00+00:00",
        bug_ref=bug_ref,
        severity=severity,
        status=status,
    )


class TestFileScarInfo:
    """Test FileScarInfo dataclass."""

    def test_total(self):
        j1 = _make_joint(bug_ref="A")
        j2 = _make_joint(bug_ref="B")
        info = FileScarInfo(file="test.py", joints=[j1, j2])
        assert info.total == 2

    def test_critical_count(self):
        j1 = _make_joint(severity="critical", bug_ref="A")
        j2 = _make_joint(severity="warning", bug_ref="B")
        info = FileScarInfo(file="test.py", joints=[j1, j2])
        assert info.critical_count == 1
        assert info.warning_count == 1

    def test_hollow_and_solid_count(self):
        j1 = _make_joint(status="solid_gold", bug_ref="A")
        j2 = _make_joint(status="hollow", bug_ref="B")
        info = FileScarInfo(file="test.py", joints=[j1, j2])
        assert info.solid_count == 1
        assert info.hollow_count == 1

    def test_empty_file(self):
        info = FileScarInfo(file="test.py")
        assert info.total == 0
        assert info.critical_count == 0


class TestDirectoryScarInfo:
    """Test DirectoryScarInfo dataclass."""

    def test_total(self):
        f1 = FileScarInfo(file="a.py", joints=[_make_joint(bug_ref="A")])
        f2 = FileScarInfo(file="b.py", joints=[_make_joint(bug_ref="B"), _make_joint(bug_ref="C")])
        d = DirectoryScarInfo(path="src", files=[f1, f2])
        assert d.total == 3

    def test_critical_count(self):
        f1 = FileScarInfo(file="a.py", joints=[_make_joint(severity="critical", bug_ref="A")])
        f2 = FileScarInfo(file="b.py", joints=[_make_joint(severity="warning", bug_ref="B")])
        d = DirectoryScarInfo(path="src", files=[f1, f2])
        assert d.critical_count == 1


class TestBuildScarMap:
    """Test building scar maps."""

    def test_empty_joints(self):
        result = build_scar_map(joints=[])
        assert result == {}

    def test_single_file(self):
        joints = [
            _make_joint(file="src/auth/login.py", bug_ref="A"),
            _make_joint(file="src/auth/login.py", bug_ref="B"),
        ]
        result = build_scar_map(joints=joints)
        assert "src/auth/login.py" in result
        assert result["src/auth/login.py"].total == 2

    def test_multiple_files(self):
        joints = [
            _make_joint(file="src/auth/login.py", bug_ref="A"),
            _make_joint(file="src/payments/charge.py", bug_ref="B"),
        ]
        result = build_scar_map(joints=joints)
        assert len(result) == 2


class TestGroupByDirectory:
    """Test grouping files by directory."""

    def test_group(self):
        file_map = {
            "src/auth/login.py": FileScarInfo(file="src/auth/login.py", joints=[_make_joint(bug_ref="A")]),
            "src/auth/oauth.py": FileScarInfo(file="src/auth/oauth.py", joints=[_make_joint(bug_ref="B")]),
        }
        result = group_by_directory(file_map)
        assert "src/auth" in result
        assert len(result["src/auth"].files) == 2


class TestFormatScarMap:
    """Test formatting scar maps."""

    def test_format_empty(self):
        result = format_scar_map({})
        assert result == ""

    def test_format_with_joints(self):
        joints = [
            _make_joint(file="src/auth/login.py", severity="critical", bug_ref="A"),
            _make_joint(file="src/auth/login.py", severity="warning", bug_ref="B"),
            _make_joint(file="src/auth/login.py", severity="warning", bug_ref="C"),
        ]
        file_map = build_scar_map(joints=joints)
        output = format_scar_map(file_map)
        assert "src/auth/" in output
        assert "login.py" in output
        assert "3 joint" in output
        assert "1 critical" in output
        assert "2 warning" in output

    def test_format_intact_file(self):
        joints = [
            _make_joint(file="src/auth/login.py", bug_ref="A"),
        ]
        file_map = build_scar_map(joints=joints)
        # Add an intact file manually
        file_map["src/auth/session.py"] = FileScarInfo(file="src/auth/session.py")
        output = format_scar_map(file_map)
        assert "intact" in output


class TestFindHotspots:
    """Test hotspot detection."""

    def test_find_hotspots(self):
        joints = [
            _make_joint(file="src/hot.py", bug_ref="A"),
            _make_joint(file="src/hot.py", bug_ref="B"),
            _make_joint(file="src/hot.py", bug_ref="C"),
            _make_joint(file="src/cool.py", bug_ref="D"),
        ]
        file_map = build_scar_map(joints=joints)
        hotspots = find_hotspots(file_map, threshold=3)
        assert len(hotspots) == 1
        assert hotspots[0][0] == "src/hot.py"
        assert hotspots[0][1] == 3

    def test_no_hotspots(self):
        joints = [
            _make_joint(file="src/cool.py", bug_ref="A"),
        ]
        file_map = build_scar_map(joints=joints)
        hotspots = find_hotspots(file_map, threshold=3)
        assert len(hotspots) == 0
