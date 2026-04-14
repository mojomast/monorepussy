"""Tests for the TUI renderer (stratagit.tui)."""

import pytest
from datetime import datetime, timezone
from stratagit.tui import render_cross_section, render_legend, render_stratum_detail
from stratagit.core import Stratum, MineralType


def _make_strata(count=3):
    """Create test strata for rendering tests."""
    strata = []
    for i in range(count):
        s = Stratum(
            commit_hash=f"abc{i:040d}",
            author=f"Author {i}",
            date=datetime(2024, 1, 15 - i, 10, 0, tzinfo=timezone.utc),
            message=f"Commit {i}",
            lines_added=10 * (i + 1),
            lines_deleted=5 * (i + 1),
            files_changed=[f"file{i}.py"],
        )
        s.stability_tier = "active"
        strata.append(s)
    return strata


class TestRenderCrossSection:
    def test_basic_render(self):
        strata = _make_strata(5)
        output = render_cross_section(strata)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_has_border(self):
        strata = _make_strata(3)
        output = render_cross_section(strata, use_color=False)
        assert "┌" in output
        assert "└" in output

    def test_header_present(self):
        strata = _make_strata(3)
        output = render_cross_section(strata, use_color=False)
        assert "STRATIGRAPHIC" in output

    def test_empty_strata(self):
        output = render_cross_section([])
        assert "no strata" in output.lower()

    def test_custom_width(self):
        strata = _make_strata(3)
        output = render_cross_section(strata, width=120, use_color=False)
        # Should respect width
        lines = output.split("\n")
        for line in lines:
            assert len(line) <= 130  # some tolerance for border chars

    def test_no_color_mode(self):
        strata = _make_strata(3)
        output = render_cross_section(strata, use_color=False)
        # Should not contain ANSI escape codes
        assert "\033[" not in output

    def test_shows_commit_hashes(self):
        strata = _make_strata(3)
        output = render_cross_section(strata, use_color=False)
        # Should contain at least partial commit hashes
        for s in strata:
            assert s.commit_hash[:8] in output


class TestRenderStratumDetail:
    def test_basic_render(self):
        s = _make_strata(1)[0]
        output = render_stratum_detail(s, use_color=False)
        assert "STRATUM DETAIL" in output

    def test_shows_hash(self):
        s = _make_strata(1)[0]
        output = render_stratum_detail(s, use_color=False)
        assert s.commit_hash in output

    def test_shows_author(self):
        s = _make_strata(1)[0]
        output = render_stratum_detail(s, use_color=False)
        assert s.author in output

    def test_shows_stability(self):
        s = _make_strata(1)[0]
        output = render_stratum_detail(s, use_color=False)
        assert "Stability" in output

    def test_shows_minerals(self):
        s = _make_strata(1)[0]
        output = render_stratum_detail(s, use_color=False)
        if s.minerals:
            assert "Minerals" in output


class TestRenderLegend:
    def test_basic_legend(self):
        output = render_legend(use_color=False)
        assert "MINERAL LEGEND" in output
        assert "THICKNESS SCALE" in output

    def test_shows_minerals(self):
        output = render_legend(use_color=False)
        # Should show at least some mineral names
        assert "pyrite" in output or "clay" in output

    def test_no_color_mode(self):
        output = render_legend(use_color=False)
        assert "\033[" not in output
