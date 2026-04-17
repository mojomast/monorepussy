"""Tests for the PatternMatcher module."""

import os
import tempfile
import pytest
from triage.patterns import PatternMatcher, SEED_PATTERNS
from triage.models import ErrorPattern, VictimType


class TestPatternMatcherInit:
    """Tests for PatternMatcher initialization."""

    def test_default_database_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_patterns.db")
            matcher = PatternMatcher(db_path=db_path)
            assert os.path.exists(db_path)
            matcher.close()

    def test_seed_patterns_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_patterns.db")
            matcher = PatternMatcher(db_path=db_path)
            count = matcher.pattern_count()
            assert count == len(SEED_PATTERNS)
            matcher.close()

    def test_seed_patterns_only_loaded_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_patterns.db")
            # Create first instance
            matcher1 = PatternMatcher(db_path=db_path)
            count1 = matcher1.pattern_count()
            matcher1.close()
            # Create second instance - should not double-seed
            matcher2 = PatternMatcher(db_path=db_path)
            count2 = matcher2.pattern_count()
            assert count1 == count2
            matcher2.close()


class TestPatternMatcherMatch:
    """Tests for the pattern matching functionality."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        self.matcher = PatternMatcher(db_path=db_path)

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_match_python_module_not_found(self):
        result = self.matcher.match(
            "ModuleNotFoundError: No module named 'requests'",
            error_type="python_error",
            language="python",
        )
        assert result is not None
        assert result.pattern_type == "python_error"
        assert "requests" in result.root_cause
        assert "pip install" in result.fix_template

    def test_match_python_import_error(self):
        result = self.matcher.match(
            "ImportError: cannot import name 'foo' from 'bar'",
            error_type="python_error",
            language="python",
        )
        assert result is not None
        assert "foo" in result.root_cause

    def test_match_python_key_error(self):
        result = self.matcher.match(
            "KeyError: 'user_id'",
            error_type="python_error",
            language="python",
        )
        assert result is not None
        assert "user_id" in result.root_cause

    def test_match_python_attribute_error(self):
        result = self.matcher.match(
            "AttributeError: 'NoneType' object has no attribute 'name'",
            error_type="python_error",
            language="python",
        )
        assert result is not None
        assert "NoneType" in result.root_cause

    def test_match_rust_trait_not_implemented(self):
        result = self.matcher.match(
            "trait `Display` is not implemented for `MyStruct`",
            error_type="rust_compile",
            language="rust",
        )
        assert result is not None
        assert "Display" in result.root_cause or "MyStruct" in result.root_cause

    def test_match_rust_cannot_find(self):
        result = self.matcher.match(
            "cannot find function `foo` in this scope",
            error_type="rust_compile",
            language="rust",
        )
        assert result is not None
        assert "foo" in result.root_cause

    def test_match_go_undefined(self):
        result = self.matcher.match(
            "undefined: ProcessData",
            error_type="go_compile",
            language="go",
        )
        assert result is not None
        assert "ProcessData" in result.root_cause

    def test_match_go_unused_import(self):
        result = self.matcher.match(
            'imported and not used: "fmt"',
            error_type="go_compile",
            language="go",
        )
        assert result is not None
        assert "fmt" in result.root_cause

    def test_match_typescript_cannot_find_module(self):
        result = self.matcher.match(
            "error TS2304: Cannot find name 'axios'",
            error_type="typescript_compile",
            language="typescript",
        )
        assert result is not None
        assert "axios" in result.root_cause

    def test_match_javascript_null_property(self):
        result = self.matcher.match(
            "TypeError: Cannot read properties of undefined (reading 'data')",
            error_type="js_runtime",
            language="javascript",
        )
        assert result is not None
        assert "data" in result.root_cause

    def test_match_cpp_undefined_reference(self):
        result = self.matcher.match(
            "undefined reference to `compute_hash'",
            error_type="cpp_compile",
            language="cpp",
        )
        assert result is not None
        assert "compute_hash" in result.root_cause

    def test_no_match_for_unknown_error(self):
        result = self.matcher.match(
            "Something completely unusual happened",
            error_type="unknown_type",
            language="brainfuck",
        )
        # May or may not match, but shouldn't crash
        assert result is None or isinstance(result, ErrorPattern)

    def test_match_returns_error_pattern(self):
        result = self.matcher.match(
            "ModuleNotFoundError: No module named 'flask'",
            error_type="python_error",
            language="python",
        )
        assert isinstance(result, ErrorPattern)
        assert result.confidence > 0
        assert result.matched_text != ""


class TestPatternMatcherCRUD:
    """Tests for adding, listing, and removing patterns."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        self.matcher = PatternMatcher(db_path=db_path)

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_custom_pattern(self):
        pid = self.matcher.add_pattern(
            pattern_type="custom",
            language="python",
            regex=r"CustomError: (.+)",
            root_cause="Custom error: {0}",
            fix_template="Fix the custom error",
            confidence=0.75,
        )
        assert pid > 0

    def test_add_and_match_custom_pattern(self):
        self.matcher.add_pattern(
            pattern_type="custom",
            language="python",
            regex=r"CustomError: (.+)",
            root_cause="Custom error occurred: {0}",
            fix_template="Fix: {0}",
            confidence=0.9,
        )
        result = self.matcher.match(
            "CustomError: database timeout",
            language="python",
        )
        assert result is not None
        assert "database timeout" in result.root_cause

    def test_add_invalid_regex_raises(self):
        with pytest.raises(ValueError, match="Invalid regex"):
            self.matcher.add_pattern(
                pattern_type="custom",
                language=None,
                regex="[invalid(regex",
                root_cause="bad",
                fix_template="worse",
            )

    def test_list_all_patterns(self):
        patterns = self.matcher.list_patterns()
        assert len(patterns) > 0

    def test_list_patterns_by_language(self):
        patterns = self.matcher.list_patterns(language="python")
        assert len(patterns) > 0
        assert all(p["language"] == "python" for p in patterns)

    def test_list_patterns_by_type(self):
        patterns = self.matcher.list_patterns(pattern_type="rust_compile")
        assert len(patterns) > 0
        assert all(p["pattern_type"] == "rust_compile" for p in patterns)

    def test_remove_custom_pattern(self):
        pid = self.matcher.add_pattern(
            pattern_type="custom",
            language=None,
            regex=r"TestError: (.+)",
            root_cause="Test: {0}",
            fix_template="Fix test",
            confidence=0.5,
        )
        assert self.matcher.remove_pattern(pid) is True

    def test_remove_nonexistent_pattern(self):
        assert self.matcher.remove_pattern(99999) is False

    def test_cannot_remove_seed_pattern(self):
        # Seed patterns have is_custom=0, so remove should fail
        assert self.matcher.remove_pattern(1) is False

    def test_pattern_count(self):
        initial = self.matcher.pattern_count()
        self.matcher.add_pattern(
            pattern_type="custom",
            language=None,
            regex=r"CountTest: (.+)",
            root_cause="Count test",
            fix_template="Fix",
            confidence=0.5,
        )
        assert self.matcher.pattern_count() == initial + 1


class TestClassifyVictim:
    """Tests for the victim classification logic."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        self.matcher = PatternMatcher(db_path=db_path)

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_victim(self):
        assert self.matcher.classify_victim("rust_compile") == VictimType.BUILD
        assert self.matcher.classify_victim("go_compile") == VictimType.BUILD
        assert self.matcher.classify_victim("cargo_build") == VictimType.BUILD

    def test_test_victim(self):
        assert self.matcher.classify_victim("test_failure") == VictimType.TEST
        assert self.matcher.classify_victim("jest_failure") == VictimType.TEST

    def test_runtime_victim(self):
        assert self.matcher.classify_victim("python_error") == VictimType.RUNTIME
        assert self.matcher.classify_victim("segfault") == VictimType.RUNTIME
        assert self.matcher.classify_victim("oom") == VictimType.RUNTIME

    def test_deployment_victim(self):
        assert self.matcher.classify_victim("github_actions") == VictimType.DEPLOYMENT
        assert self.matcher.classify_victim("gitlab_ci") == VictimType.DEPLOYMENT

    def test_unknown_victim(self):
        assert self.matcher.classify_victim("unknown_type") == VictimType.UNKNOWN
