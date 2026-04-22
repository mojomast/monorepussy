"""Tests for mental context capture."""

import os
from datetime import datetime, timezone
from unittest.mock import patch

from ussy_snapshot.context import (
    capture_mental_context,
    format_context_display,
    _auto_suggest_context,
)
from ussy_snapshot.models import MentalContext


class TestCaptureMentalContext:
    def test_basic_capture(self):
        ctx = capture_mental_context(note="About to fix the callback")
        assert ctx.note == "About to fix the callback"
        assert ctx.timestamp != ""

    def test_timestamp_is_utc(self):
        ctx = capture_mental_context()
        dt = datetime.fromisoformat(ctx.timestamp)
        assert dt.tzinfo is not None

    def test_empty_note(self):
        ctx = capture_mental_context()
        assert ctx.note == ""

    def test_with_project_dir(self):
        ctx = capture_mental_context(note="test", project_dir=os.getcwd())
        assert ctx.note == "test"

    def test_auto_suggestion_populated(self):
        """Auto suggestion should be generated (may be empty if not in git repo)."""
        ctx = capture_mental_context()
        assert isinstance(ctx.auto_suggestion, str)


class TestAutoSuggestContext:
    def test_returns_string(self):
        result = _auto_suggest_context("", "", "")
        assert isinstance(result, str)

    def test_includes_branch(self):
        result = _auto_suggest_context("", "feature-auth", "clean")
        assert "feature-auth" in result

    def test_includes_status(self):
        result = _auto_suggest_context("", "main", "3 modified")
        assert "3 modified" in result

    def test_empty_state(self):
        result = _auto_suggest_context("", "", "")
        assert isinstance(result, str)


class TestFormatContextDisplay:
    def test_format_with_note(self):
        ctx = MentalContext(note="Was about to wire up the callback handler")
        display = format_context_display(ctx)
        assert "MENTAL CONTEXT" in display
        assert "Was about to wire up the callback handler" in display

    def test_format_without_note(self):
        ctx = MentalContext()
        display = format_context_display(ctx)
        assert "MENTAL CONTEXT" in display

    def test_format_with_branch(self):
        ctx = MentalContext(git_branch="feature-oauth")
        display = format_context_display(ctx)
        assert "feature-oauth" in display

    def test_format_with_timestamp(self):
        ctx = MentalContext()
        display = format_context_display(ctx)
        assert ctx.timestamp in display

    def test_format_includes_separators(self):
        ctx = MentalContext(note="test")
        display = format_context_display(ctx)
        assert "=" * 60 in display
