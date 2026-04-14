"""Tests for the scanner module."""

import tempfile
from pathlib import Path

import pytest

from kintsugi.scanner import (
    parse_inline_joint,
    scan_file,
    scan_directory,
    insert_annotation,
    JOINT_HEADER_RE,
)
from kintsugi.joint import Joint


# ── Test fixtures ──

SAMPLE_FILE_WITH_JOINTS = '''\
# ⛩️ KINTSUGI JOINT: 2024-03-15 | PROJ-892 | CRITICAL
# BREAK: user.email was None when OAuth provider returned empty dict
# REPAIR: Added None guard before .lower() call
# IF REMOVED: TypeError crash on login for OAuth users with no email
# STRESS TEST: test_oauth_null_email_crash (mutant: remove guard → FAIL)
def normalize_email(user):
    if user.email is not None:
        return user.email.lower().strip()
    return ""

def other_function():
    pass
'''

SAMPLE_FILE_NO_JOINTS = '''\
def hello():
    print("hello")

def goodbye():
    print("goodbye")
'''

SAMPLE_FILE_MULTIPLE_JOINTS = '''\
# ⛩️ KINTSUGI JOINT: 2024-03-15 | PROJ-892 | CRITICAL
# BREAK: user.email was None
# REPAIR: Added None guard
def normalize_email(user):
    if user.email is not None:
        return user.email.lower().strip()
    return ""

# ⛩️ KINTSUGI JOINT: 2024-07-20 | PROJ-1203 | WARNING
# BREAK: Race condition on concurrent charges
# REPAIR: Added advisory lock
def process_charge(amount):
    with lock:
        return charge(amount)
'''


class TestParseInlineJoint:
    """Test parsing of inline golden joint annotations."""

    def test_parse_full_annotation(self):
        lines = SAMPLE_FILE_WITH_JOINTS.splitlines()
        result = parse_inline_joint(lines, 0)
        assert result is not None
        assert result["timestamp"] == "2024-03-15"
        assert result["bug_ref"] == "PROJ-892"
        assert result["severity"] == "critical"
        assert result["break_description"] == "user.email was None when OAuth provider returned empty dict"
        assert result["repair_description"] == "Added None guard before .lower() call"
        assert result["removal_impact"] == "TypeError crash on login for OAuth users with no email"
        assert result["test_ref"] == "test_oauth_null_email_crash"
        assert result["line"] == 1

    def test_parse_minimal_annotation(self):
        text = "# ⛩️ KINTSUGI JOINT: 2024-01-01 | X-1 | WARNING\n"
        lines = text.splitlines()
        result = parse_inline_joint(lines, 0)
        assert result is not None
        assert result["bug_ref"] == "X-1"
        assert result["severity"] == "warning"

    def test_parse_non_matching_line(self):
        lines = ["def foo():", "    pass"]
        result = parse_inline_joint(lines, 0)
        assert result is None

    def test_line_number_is_1_indexed(self):
        text = "# ⛩️ KINTSUGI JOINT: 2024-01-01 | X-1 | INFO\n"
        lines = text.splitlines()
        result = parse_inline_joint(lines, 0)
        assert result is not None
        assert result["line"] == 1


class TestScanFile:
    """Test scanning files for golden joints."""

    def test_scan_file_with_joints(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_FILE_WITH_JOINTS)
        result = scan_file(str(f))
        assert len(result.joints) == 1
        assert result.joints[0].bug_ref == "PROJ-892"
        assert result.errors == []

    def test_scan_file_no_joints(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_FILE_NO_JOINTS)
        result = scan_file(str(f))
        assert len(result.joints) == 0

    def test_scan_file_multiple_joints(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_FILE_MULTIPLE_JOINTS)
        result = scan_file(str(f))
        assert len(result.joints) == 2
        refs = [j.bug_ref for j in result.joints]
        assert "PROJ-892" in refs
        assert "PROJ-1203" in refs

    def test_scan_nonexistent_file(self):
        result = scan_file("/nonexistent/file.py")
        assert len(result.errors) > 0
        assert len(result.joints) == 0

    def test_scan_file_sets_file_path(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_FILE_WITH_JOINTS)
        result = scan_file(str(f))
        assert result.joints[0].file == str(f)


class TestScanDirectory:
    """Test scanning directories for golden joints."""

    def test_scan_directory(self, tmp_path):
        f1 = tmp_path / "a.py"
        f1.write_text(SAMPLE_FILE_WITH_JOINTS)
        f2 = tmp_path / "b.py"
        f2.write_text(SAMPLE_FILE_NO_JOINTS)

        results = scan_directory(str(tmp_path))
        assert len(results) == 2

    def test_scan_directory_recursive(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        f1 = tmp_path / "a.py"
        f1.write_text(SAMPLE_FILE_WITH_JOINTS)
        f2 = subdir / "b.py"
        f2.write_text(SAMPLE_FILE_WITH_JOINTS)

        results = scan_directory(str(tmp_path))
        assert len(results) == 2

    def test_scan_directory_skips_hidden(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        f1 = hidden / "a.py"
        f1.write_text(SAMPLE_FILE_WITH_JOINTS)

        results = scan_directory(str(tmp_path))
        assert len(results) == 0

    def test_scan_nonexistent_directory(self):
        results = scan_directory("/nonexistent/dir")
        assert results == []


class TestInsertAnnotation:
    """Test inserting golden joint annotations into source files."""

    def test_insert_annotation(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    pass\n")

        insert_annotation(
            file_path=str(f),
            line_number=2,
            bug_ref="PROJ-1",
            severity="critical",
            break_description="null pointer",
            repair_description="added guard",
            removal_impact="crash",
            test_ref="test_foo",
        )

        content = f.read_text()
        assert "⛩️ KINTSUGI JOINT" in content
        assert "PROJ-1" in content
        assert "CRITICAL" in content
        assert "BREAK: null pointer" in content
        assert "REPAIR: added guard" in content
        assert "IF REMOVED: crash" in content
        assert "STRESS TEST: test_foo" in content

    def test_insert_annotation_minimal(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\ny = 2\n")

        insert_annotation(
            file_path=str(f),
            line_number=1,
            bug_ref="X-1",
            severity="info",
            break_description="bug",
            repair_description="fix",
        )

        content = f.read_text()
        assert "⛩️ KINTSUGI JOINT" in content
        assert "IF REMOVED" not in content  # not provided
        assert "STRESS TEST" not in content  # not provided

    def test_insert_annotation_line_1(self, tmp_path):
        f = tmp_path / "test.py"
        original = "def foo():\n    pass\n"
        f.write_text(original)

        insert_annotation(
            file_path=str(f),
            line_number=1,
            bug_ref="X-1",
            severity="warning",
            break_description="b",
            repair_description="r",
        )

        content = f.read_text()
        lines = content.splitlines()
        # First line should now be the annotation
        assert "⛩️ KINTSUGI JOINT" in lines[0]


class TestJointHeaderRegex:
    """Test the JOINT_HEADER_RE pattern."""

    def test_matches_critical(self):
        m = JOINT_HEADER_RE.match("# ⛩️ KINTSUGI JOINT: 2024-03-15 | PROJ-892 | CRITICAL")
        assert m is not None
        assert m.group(1).strip() == "2024-03-15"
        assert m.group(2).strip() == "PROJ-892"
        assert m.group(3).strip() == "CRITICAL"

    def test_matches_warning(self):
        m = JOINT_HEADER_RE.match("# ⛩️ KINTSUGI JOINT: 2024-01-01 | BUG-42 | WARNING")
        assert m is not None

    def test_no_match_without_torii(self):
        m = JOINT_HEADER_RE.match("# KINTSUGI JOINT: 2024-01-01 | BUG-42 | WARNING")
        assert m is None
