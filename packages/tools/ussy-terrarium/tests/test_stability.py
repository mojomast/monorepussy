"""Tests for the stability classification module."""

import pytest

from terrarium.metrics.stability import (
    classify_stability,
    classify_age,
    is_likely_dead,
    is_likely_generated,
    is_likely_config,
    is_likely_entry_point,
    is_likely_test,
    is_likely_deprecated,
)


class TestClassifyStability:
    """Tests for stability tier classification."""

    def test_seedling(self):
        """Recently changed files are seedlings."""
        assert classify_stability(5) == "seedling"
        assert classify_stability(0) == "seedling"
        assert classify_stability(30) == "seedling"

    def test_sapling(self):
        """Moderately stable files are saplings."""
        assert classify_stability(31) == "sapling"
        assert classify_stability(100) == "sapling"
        assert classify_stability(180) == "sapling"

    def test_mature(self):
        """Stable files are mature."""
        assert classify_stability(181) == "mature"
        assert classify_stability(365) == "mature"
        assert classify_stability(730) == "mature"

    def test_old_growth(self):
        """Ancient, barely changed files are old-growth."""
        assert classify_stability(731) == "old_growth"
        assert classify_stability(1000) == "old_growth"
        assert classify_stability(3650) == "old_growth"


class TestClassifyAge:
    """Tests for age tier classification."""

    def test_newborn(self):
        assert classify_age(0) == "newborn"
        assert classify_age(7) == "newborn"

    def test_young(self):
        assert classify_age(8) == "young"
        assert classify_age(90) == "young"

    def test_established(self):
        assert classify_age(91) == "established"
        assert classify_age(365) == "established"

    def test_old(self):
        assert classify_age(366) == "old"
        assert classify_age(3650) == "old"


class TestIsLikelyDead:
    """Tests for dead code heuristic."""

    def test_not_dead_recent(self):
        """Recently changed code is not dead."""
        assert is_likely_dead(10) is False
        assert is_likely_dead(100) is False

    def test_dead_very_old(self):
        """Very old unchanged code is likely dead."""
        assert is_likely_dead(731) is True
        assert is_likely_dead(1000) is True

    def test_dead_deprecated(self):
        """Deprecated + somewhat old = dead."""
        assert is_likely_dead(200, is_deprecated=True) is True
        assert is_likely_dead(50, is_deprecated=True) is False

    def test_not_dead_new_deprecated(self):
        """Recently changed deprecated code is not dead."""
        assert is_likely_dead(30, is_deprecated=True) is False


class TestIsLikelyGenerated:
    """Tests for generated file heuristic."""

    def test_generated_patterns(self):
        """Files with generated patterns are detected."""
        assert is_likely_generated("api_generated.py") is True
        assert is_likely_generated("types.generated.py") is True
        assert is_likely_generated("api_pb2.py") is True
        assert is_likely_generated("api_pb.py") is True

    def test_normal_files(self):
        """Normal Python files are not generated."""
        assert is_likely_generated("main.py") is False
        assert is_likely_generated("utils.py") is False
        assert is_likely_generated("models.py") is False


class TestIsLikelyConfig:
    """Tests for config file heuristic."""

    def test_config_patterns(self):
        assert is_likely_config("config.py") is True
        assert is_likely_config("settings.py") is True
        assert is_likely_config("conftest.py") is True

    def test_non_config(self):
        assert is_likely_config("main.py") is False
        assert is_likely_config("models.py") is False


class TestIsLikelyEntryPoint:
    """Tests for entry point heuristic."""

    def test_entry_points(self):
        assert is_likely_entry_point("main.py") is True
        assert is_likely_entry_point("app.py") is True
        assert is_likely_entry_point("manage.py") is True
        assert is_likely_entry_point("cli.py") is True

    def test_not_entry_point(self):
        assert is_likely_entry_point("utils.py") is False
        assert is_likely_entry_point("models.py") is False


class TestIsLikelyTest:
    """Tests for test file heuristic."""

    def test_test_files(self):
        assert is_likely_test("test_main.py") is True
        assert is_likely_test("tests/test_foo.py") is True
        assert is_likely_test("src/test_bar.py") is True

    def test_not_test(self):
        assert is_likely_test("main.py") is False
        assert is_likely_test("testing_utils.py") is False


class TestIsLikelyDeprecated:
    """Tests for deprecated file heuristic."""

    def test_deprecated_in_name(self):
        assert is_likely_deprecated("deprecated_module.py") is True
        assert is_likely_deprecated("legacy_handler.py") is True

    def test_deprecated_in_source(self):
        source = "# DEPRECATED: this module is old\nstuff = True\n"
        assert is_likely_deprecated("module.py", source) is True

    def test_not_deprecated(self):
        assert is_likely_deprecated("utils.py") is False
        assert is_likely_deprecated("handler.py", "# Regular module\n") is False
