"""Tests for the static export renderer."""

import os
import tempfile

import pytest

from terrarium.ecosystem.organisms import OrganismType, Vitality
from terrarium.ecosystem.model import Organism, Ecosystem
from terrarium.renderers.static_export import (
    render_text_snapshot,
    render_svg_snapshot,
    export_snapshot,
)


class TestRenderTextSnapshot:
    """Tests for plain text snapshot rendering."""

    def test_text_snapshot(self):
        """Render a plain text snapshot."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90, organism_type=OrganismType.BUSH),
            "b.py": Organism(path="b.py", health=30, organism_type=OrganismType.BUSH,
                              symptoms=["Low coverage"]),
        }
        eco.compute_stats()
        output = render_text_snapshot(eco)
        assert "TERRARIUM" in output
        assert "a.py" in output
        assert "b.py" in output
        # No ANSI codes in text snapshot
        assert "\033[" not in output

    def test_text_snapshot_empty(self):
        """Empty ecosystem renders without error."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.compute_stats()
        output = render_text_snapshot(eco)
        assert "TERRARIUM" in output


class TestRenderSvgSnapshot:
    """Tests for SVG snapshot rendering."""

    def test_svg_snapshot(self):
        """Render an SVG snapshot."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90, organism_type=OrganismType.TREE),
        }
        eco.compute_stats()
        output = render_svg_snapshot(eco)
        assert "<svg" in output
        assert "</svg>" in output
        assert "Terrarium" in output

    def test_svg_empty_ecosystem(self):
        """Empty ecosystem renders minimal SVG."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.compute_stats()
        output = render_svg_snapshot(eco)
        assert "<svg" in output
        assert "No organisms" in output

    def test_svg_many_organisms(self):
        """SVG handles many organisms with grid layout."""
        eco = Ecosystem(root_path="/tmp/test")
        for i in range(10):
            eco.organisms[f"file_{i}.py"] = Organism(
                path=f"file_{i}.py", health=50 + i * 5,
                organism_type=OrganismType.BUSH,
            )
        eco.compute_stats()
        output = render_svg_snapshot(eco)
        assert "<svg" in output


class TestExportSnapshot:
    """Tests for snapshot file export."""

    def test_export_text(self):
        """Export a text snapshot to file."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
        }
        eco.compute_stats()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "report.txt")
            export_snapshot(eco, filepath, format="text")
            assert os.path.exists(filepath)
            with open(filepath) as f:
                content = f.read()
            assert "TERRARIUM" in content

    def test_export_svg(self):
        """Export an SVG snapshot to file."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90, organism_type=OrganismType.TREE),
        }
        eco.compute_stats()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "report.svg")
            export_snapshot(eco, filepath, format="svg")
            assert os.path.exists(filepath)
            with open(filepath) as f:
                content = f.read()
            assert "<svg" in content
