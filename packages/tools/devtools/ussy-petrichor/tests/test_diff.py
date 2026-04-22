"""Tests for petrichor.diff module."""

from ussy_petrichor.diff import compute_diff, diff_stats, extract_changed_keys, lines_changed


class TestComputeDiff:
    def test_no_change(self):
        result = compute_diff("hello\n", "hello\n")
        assert result == ""

    def test_simple_addition(self):
        old = "line1\n"
        new = "line1\nline2\n"
        result = compute_diff(old, new)
        assert "+line2" in result

    def test_simple_removal(self):
        old = "line1\nline2\n"
        new = "line1\n"
        result = compute_diff(old, new)
        assert "-line2" in result

    def test_modification(self):
        old = "key=old\n"
        new = "key=new\n"
        result = compute_diff(old, new)
        assert "-key=old" in result
        assert "+key=new" in result

    def test_empty_to_content(self):
        result = compute_diff("", "new content\n")
        assert "+new content" in result

    def test_content_to_empty(self):
        result = compute_diff("old content\n", "")
        assert "-old content" in result

    def test_context_lines(self):
        old = "a\nb\nc\nd\ne\n"
        new = "a\nb\nX\nd\ne\n"
        result = compute_diff(old, new, context_lines=1)
        assert "c" in result or "X" in result


class TestDiffStats:
    def test_additions(self):
        diff = "--- a\n+++ b\n+line1\n+line2\n"
        result = diff_stats(diff)
        assert result["added"] == 2
        assert result["removed"] == 0

    def test_removals(self):
        diff = "--- a\n+++ b\n-line1\n-line2\n"
        result = diff_stats(diff)
        assert result["added"] == 0
        assert result["removed"] == 2

    def test_mixed(self):
        diff = "--- a\n+++ b\n-old\n+new\n"
        result = diff_stats(diff)
        assert result["added"] == 1
        assert result["removed"] == 1

    def test_empty_diff(self):
        result = diff_stats("")
        assert result["added"] == 0
        assert result["removed"] == 0


class TestExtractChangedKeys:
    def test_equals_separator(self):
        old = "key1=val1\nkey2=val2\n"
        new = "key1=val1\nkey2=changed\n"
        result = extract_changed_keys(old, new)
        assert "key2" in result

    def test_colon_separator(self):
        old = "key1: val1\nkey2: val2\n"
        new = "key1: val1\nkey2: changed\n"
        result = extract_changed_keys(old, new)
        assert "key2" in result

    def test_no_change(self):
        old = "key=val\n"
        new = "key=val\n"
        result = extract_changed_keys(old, new)
        assert result == []

    def test_comments_ignored(self):
        old = "# comment1\nkey=val\n"
        new = "# comment2\nkey=val\n"
        result = extract_changed_keys(old, new)
        assert result == []

    def test_added_key(self):
        old = "key1=val1\n"
        new = "key1=val1\nkey2=val2\n"
        result = extract_changed_keys(old, new)
        assert "key2" in result


class TestLinesChanged:
    def test_no_change(self):
        result = lines_changed("same\n", "same\n")
        assert result == 0

    def test_both_empty(self):
        result = lines_changed("", "")
        assert result is None

    def test_some_changes(self):
        result = lines_changed("a\nb\nc\n", "a\nX\nc\n")
        assert result is not None
        assert result >= 1
