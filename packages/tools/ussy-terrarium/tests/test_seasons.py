"""Tests for the seasonal view renderer."""

import pytest

from terrarium.ecosystem.organisms import OrganismType, Vitality
from terrarium.ecosystem.model import Organism, Ecosystem
from terrarium.renderers.seasons import classify_season, render_seasons_view


class TestClassifySeason:
    """Tests for season classification."""

    def test_winter_old_unchanged(self):
        """Very old unchanged code is in winter."""
        assert classify_season(0.5, 0.5, 400) == "winter"

    def test_autumn_stale(self):
        """Somewhat stale code is in autumn."""
        assert classify_season(0.5, 0.5, 200) == "autumn"

    def test_spring_rapid_untested(self):
        """Rapid, untested growth is spring."""
        assert classify_season(5.0, 0.2, 10) == "spring"

    def test_summer_active(self):
        """Active, maintained code is summer."""
        assert classify_season(2.0, 0.7, 30) == "summer"

    def test_summer_well_tested(self):
        """Well-tested code is summer even if slow."""
        assert classify_season(1.5, 0.9, 20) == "summer"


class TestRenderSeasonsView:
    """Tests for the seasons view renderer."""

    def test_render_with_organisms(self):
        """Render seasons view with organisms."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "new_feature.py": Organism(
                path="new_feature.py", health=70,
                organism_type=OrganismType.SEEDLING,
                stability_tier="seedling",
            ),
            "stable.py": Organism(
                path="stable.py", health=90,
                organism_type=OrganismType.TREE,
                stability_tier="mature",
            ),
            "old_code.py": Organism(
                path="old_code.py", health=10,
                organism_type=OrganismType.DEAD_WOOD,
                stability_tier="old_growth",
            ),
        }
        eco.compute_stats()
        output = render_seasons_view(eco)
        assert "SEASONAL VIEW" in output
        assert "Spring" in output or "spring" in output.lower()

    def test_render_with_history(self):
        """Render seasons view with git history."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=70, organism_type=OrganismType.BUSH),
        }
        eco.compute_stats()
        history = [
            {"month": "2025-01", "count": 10},
            {"month": "2025-02", "count": 25},
            {"month": "2025-03", "count": 5},
        ]
        output = render_seasons_view(eco, history)
        assert "Timeline" in output
        assert "2025-01" in output

    def test_render_empty_ecosystem(self):
        """Empty ecosystem renders without error."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.compute_stats()
        output = render_seasons_view(eco)
        assert "SEASONAL VIEW" in output
