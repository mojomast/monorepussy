"""Tests for ASCII renderer."""
import pytest
from ussy_stratax.models import (
    BedrockReport,
    DiffResult,
    ErosionReport,
    FaultLine,
    ScanResult,
    StratigraphicColumn,
)
from ussy_stratax.render.ascii import ASCIIRenderer


class TestASCIIRenderer:
    def setup_method(self):
        self.renderer = ASCIIRenderer(use_color=False)

    def test_render_column_empty(self):
        col = StratigraphicColumn(package="testpkg")
        output = self.renderer.render_column(col)
        assert "testpkg" in output
        assert "stratigraphic column" in output

    def test_render_column_with_bedrock(self):
        col = StratigraphicColumn(
            package="testpkg",
            bedrock_reports=[
                BedrockReport("testpkg", "stable_fn", 95.0, 9, 10, 3.0),
            ],
        )
        output = self.renderer.render_column(col)
        assert "stable_fn" in output
        assert "bedrock" in output

    def test_render_column_with_faults(self):
        col = StratigraphicColumn(
            package="testpkg",
            bedrock_reports=[
                BedrockReport("testpkg", "good_fn", 95.0, 9, 10, 3.0),
                BedrockReport("testpkg", "bad_fn", 10.0, 1, 10, 0.0),
            ],
            fault_lines=[
                FaultLine("testpkg", "good_fn", "bad_fn", 95.0, 10.0),
            ],
        )
        output = self.renderer.render_column(col)
        assert "fault line" in output.lower()

    def test_render_column_no_hazards(self):
        col = StratigraphicColumn(
            package="testpkg",
            bedrock_reports=[
                BedrockReport("testpkg", "fn1", 95.0, 9, 10, 3.0),
            ],
        )
        output = self.renderer.render_column(col)
        assert "No hazards" in output

    def test_render_scan_result_no_hazards(self):
        result = ScanResult(lockfile="test.lock", packages_scanned=5)
        output = self.renderer.render_scan_result(result)
        assert "No seismic hazards" in output
        assert "5" in output

    def test_render_scan_result_with_faults(self):
        result = ScanResult(
            lockfile="test.lock",
            fault_lines=[
                FaultLine("pkg", "stable_fn", "unstable_fn", 95.0, 10.0, "Gap detected"),
            ],
            packages_scanned=3,
        )
        output = self.renderer.render_scan_result(result)
        assert "FAULT LINE" in output
        assert "pkg" in output

    def test_render_scan_result_with_quicksand(self):
        result = ScanResult(
            lockfile="test.lock",
            quicksand_zones=[
                BedrockReport("pkg", "fn", 10.0, 1, 10, 0.0),
            ],
            packages_scanned=2,
        )
        output = self.renderer.render_scan_result(result)
        assert "QUICKSAND" in output

    def test_render_scan_result_with_erosion(self):
        result = ScanResult(
            lockfile="test.lock",
            erosion_warnings=[
                ErosionReport("pkg", "fn", -0.05, 1.0, 0.7, 5, True),
            ],
            packages_scanned=2,
        )
        output = self.renderer.render_scan_result(result)
        assert "EROSION" in output

    def test_render_diff_result_no_quakes(self):
        diff = DiffResult(
            package="pkg",
            version_a="1.0.0",
            version_b="2.0.0",
            unchanged_count=5,
        )
        output = self.renderer.render_diff_result(diff)
        assert "No behavioral changes" in output or "unchanged" in output.lower()

    def test_render_diff_result_with_quakes(self):
        diff = DiffResult(
            package="pkg",
            version_a="1.0.0",
            version_b="2.0.0",
            behavioral_quakes=[
                {"probe": "p1", "description": "p1 changed"},
            ],
        )
        output = self.renderer.render_diff_result(diff)
        assert "quake" in output.lower()

    def test_color_mode(self):
        renderer = ASCIIRenderer(use_color=True)
        col = StratigraphicColumn(
            package="testpkg",
            bedrock_reports=[
                BedrockReport("testpkg", "fn", 95.0, 9, 10, 3.0),
            ],
        )
        output = renderer.render_column(col)
        # Should contain ANSI escape codes
        assert "\033[" in output

    def test_render_diff_with_new_and_removed(self):
        diff = DiffResult(
            package="pkg",
            version_a="1.0",
            version_b="2.0",
            new_behaviors=["new_probe"],
            removed_behaviors=["old_probe"],
        )
        output = self.renderer.render_diff_result(diff)
        assert "new_probe" in output
        assert "old_probe" in output
