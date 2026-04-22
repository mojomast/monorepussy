"""Tests for mint.composition — Fineness and alloy analysis."""

import pytest
from mint.composition import (
    compute_fineness,
    categorize_alloy,
    compute_maintainer_overlap,
    analyze_license_mix,
    compute_composition,
)


class TestComputeFineness:
    """Test fineness (purity ratio) calculation."""

    def test_pure_package(self):
        """All own code → fineness = 1.0."""
        assert compute_fineness(1000, 0, 0) == 1.0

    def test_fully_vendored(self):
        """No own code → fineness = 0.0."""
        assert compute_fineness(0, 1000, 0) == 0.0

    def test_mixed_composition(self):
        """75% own code → fineness ≈ 0.75."""
        result = compute_fineness(750, 200, 50)
        assert abs(result - 0.75) < 0.01

    def test_zero_total(self):
        """Zero total → fineness = 1.0 (no code is pure by default)."""
        assert compute_fineness(0, 0, 0) == 1.0

    def test_bundled_code_reduces_fineness(self):
        """Bundled code should reduce fineness."""
        pure = compute_fineness(1000, 0, 0)
        bundled = compute_fineness(1000, 0, 500)
        assert bundled < pure

    def test_vendored_and_bundled(self):
        """Both vendored and bundled reduce fineness."""
        result = compute_fineness(500, 250, 250)
        assert result == 0.5


class TestCategorizeAlloy:
    """Test dependency categorization."""

    def test_empty_dependencies(self):
        result = categorize_alloy([])
        assert result == {"core": 0, "build": 0, "test": 0, "filler": 0, "contaminant": 0}

    def test_core_dependencies(self):
        deps = [{"name": "lodash", "category": "core"}]
        result = categorize_alloy(deps)
        assert result["core"] == 1
        assert result["build"] == 0

    def test_mixed_categories(self):
        deps = [
            {"name": "react", "category": "core"},
            {"name": "webpack", "category": "build"},
            {"name": "jest", "category": "test"},
            {"name": "old-polyfill", "category": "filler"},
            {"name": "vuln-pkg", "category": "contaminant"},
        ]
        result = categorize_alloy(deps)
        assert result["core"] == 1
        assert result["build"] == 1
        assert result["test"] == 1
        assert result["filler"] == 1
        assert result["contaminant"] == 1

    def test_unknown_category_goes_to_filler(self):
        deps = [{"name": "weird-dep", "category": "unknown_category"}]
        result = categorize_alloy(deps)
        assert result["filler"] == 1

    def test_missing_category_defaults_to_core(self):
        deps = [{"name": "no-category"}]
        result = categorize_alloy(deps)
        assert result["core"] == 1


class TestComputeMaintainerOverlap:
    """Test maintainer overlap calculation."""

    def test_no_overlap(self):
        maintainers = {
            "pkg-a": ["alice"],
            "pkg-b": ["bob"],
        }
        assert compute_maintainer_overlap(maintainers) == 0.0

    def test_full_overlap(self):
        maintainers = {
            "pkg-a": ["alice", "bob"],
            "pkg-b": ["alice", "bob"],
        }
        assert compute_maintainer_overlap(maintainers) == 1.0

    def test_partial_overlap(self):
        maintainers = {
            "pkg-a": ["alice", "bob"],
            "pkg-b": ["bob", "charlie"],
            "pkg-c": ["dave"],
        }
        overlap = compute_maintainer_overlap(maintainers)
        # (a,b) overlap, (a,c) no, (b,c) no = 1/3
        assert abs(overlap - 1/3) < 0.01

    def test_single_package(self):
        maintainers = {"pkg-a": ["alice"]}
        assert compute_maintainer_overlap(maintainers) == 0.0

    def test_empty_dict(self):
        assert compute_maintainer_overlap({}) == 0.0


class TestAnalyzeLicenseMix:
    """Test license mix analysis."""

    def test_empty(self):
        result = analyze_license_mix([])
        assert result == {}

    def test_single_license(self):
        result = analyze_license_mix(["MIT"])
        assert result == {"MIT": 1}

    def test_mixed_licenses(self):
        licenses = ["MIT", "Apache-2.0", "MIT", "GPL-3.0", "MIT"]
        result = analyze_license_mix(licenses)
        assert result["MIT"] == 3
        assert result["Apache-2.0"] == 1
        assert result["GPL-3.0"] == 1

    def test_unknown_license(self):
        result = analyze_license_mix([""])
        assert result["UNKNOWN"] == 1


class TestComputeComposition:
    """Test full composition analysis."""

    def test_default_composition(self):
        comp = compute_composition()
        assert comp.own_code_ratio == 1.0
        assert comp.transitive_count == 0

    def test_full_composition(self):
        deps = [
            {"name": "react", "category": "core"},
            {"name": "jest", "category": "test"},
        ]
        maintainers = {
            "react": ["acdlite", "gaearon"],
            "jest": ["cpojer", "gaearon"],
        }
        comp = compute_composition(
            own_loc=5000,
            vendored_loc=500,
            dependencies=deps,
            maintainers_per_pkg=maintainers,
            licenses=["MIT", "MIT", "Apache-2.0"],
            transitive_depth=3,
        )
        assert comp.own_code_ratio < 1.0
        assert comp.transitive_count == 2
        assert comp.alloy_breakdown["core"] == 1
        assert comp.alloy_breakdown["test"] == 1
        assert comp.maintainer_overlap > 0
        assert "MIT" in comp.license_mix
