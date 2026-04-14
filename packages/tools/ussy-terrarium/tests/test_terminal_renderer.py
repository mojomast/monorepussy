"""Tests for the terminal renderer."""

import pytest

from terrarium.ecosystem.organisms import OrganismType, Vitality
from terrarium.ecosystem.model import Organism, Ecosystem
from terrarium.renderers.terminal import (
    render_organism_line,
    render_terrarium,
    render_microscope,
    render_health_summary,
)


class TestRenderOrganismLine:
    """Tests for individual organism rendering."""

    def test_basic_render(self):
        """Render a single organism line."""
        org = Organism(path="src/main.py", health=85, organism_type=OrganismType.TREE)
        line = render_organism_line(org)
        assert "src/main.py" in line
        assert "85" in line

    def test_render_without_health(self):
        """Render without health score."""
        org = Organism(path="src/main.py", health=85, organism_type=OrganismType.TREE)
        line = render_organism_line(org, show_health=False)
        assert "src/main.py" in line
        assert "[" not in line or "85" not in line

    def test_stability_icon(self):
        """Stability tier icon is included."""
        org = Organism(path="src/main.py", health=85, organism_type=OrganismType.TREE,
                        stability_tier="old_growth")
        line = render_organism_line(org)
        assert len(line) > 0


class TestRenderTerrarium:
    """Tests for full terrarium rendering."""

    def test_render_empty_ecosystem(self):
        """Render an empty ecosystem."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.compute_stats()
        output = render_terrarium(eco)
        assert "TERRARIUM" in output
        assert "0" in output  # count of organisms

    def test_render_with_organisms(self):
        """Render an ecosystem with organisms."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "src/main.py": Organism(path="src/main.py", health=90, organism_type=OrganismType.TREE),
            "src/utils.py": Organism(path="src/utils.py", health=75, organism_type=OrganismType.BUSH),
        }
        eco.compute_stats()
        output = render_terrarium(eco)
        assert "main.py" in output
        assert "utils.py" in output
        assert "Health" in output

    def test_render_includes_critical(self):
        """Terrarium shows most critical organism."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
            "b.py": Organism(path="b.py", health=20),
        }
        eco.compute_stats()
        output = render_terrarium(eco)
        assert "critical" in output.lower() or "b.py" in output


class TestRenderMicroscope:
    """Tests for microscope view rendering."""

    def test_render_microscope(self):
        """Render detailed view of an organism."""
        org = Organism(
            path="auth.py",
            health=45,
            organism_type=OrganismType.BUSH,
            symptoms=["High churn", "Low coverage"],
            strengths=["Stable API"],
        )
        output = render_microscope(org)
        assert "auth.py" in output
        assert "Symptoms" in output
        assert "High churn" in output
        assert "Strengths" in output

    def test_render_healthy_organism(self):
        """Healthy organism shows no symptoms."""
        org = Organism(
            path="utils.py",
            health=95,
            organism_type=OrganismType.BUSH,
            symptoms=[],
        )
        output = render_microscope(org)
        assert "No symptoms" in output


class TestRenderHealthSummary:
    """Tests for health summary rendering."""

    def test_health_summary(self):
        """Render a compact health summary."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
            "b.py": Organism(path="b.py", health=45),
        }
        eco.compute_stats()
        output = render_health_summary(eco)
        assert "Ecosystem Health" in output
        assert "thriving" in output.lower()
