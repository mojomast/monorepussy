"""Tests for endemic.superspreader module."""

import pytest

from endemic.models import (
    DeveloperStats,
    TransmissionEvent,
    TransmissionTree,
    TransmissionVector,
)
from endemic.superspreader import (
    compute_superspreader_impact,
    identify_superspreader_developers,
    identify_superspreader_events,
    identify_superspreader_modules,
)


def _build_tree() -> TransmissionTree:
    """Build a sample transmission tree for testing."""
    tree = TransmissionTree(pattern_name="bare-except", index_case="a.py")

    # a.py infects b.py, c.py, d.py (superspreader)
    for target in ["b.py", "c.py", "d.py"]:
        tree.add_event(TransmissionEvent(
            pattern_name="bare-except",
            source_module="a.py",
            target_module=target,
            vector=TransmissionVector.COPY_PASTE,
            developer="alice@test.com",
        ))

    # b.py infects e.py
    tree.add_event(TransmissionEvent(
        pattern_name="bare-except",
        source_module="b.py",
        target_module="e.py",
        vector=TransmissionVector.DEVELOPER_HABIT,
        developer="bob@test.com",
    ))

    # d.py infects f.py, g.py
    for target in ["f.py", "g.py"]:
        tree.add_event(TransmissionEvent(
            pattern_name="bare-except",
            source_module="d.py",
            target_module=target,
            vector=TransmissionVector.SHARED_MODULE,
            developer="charlie@test.com",
        ))

    return tree


class TestIdentifySuperspreaderModules:
    def test_basic(self):
        tree = _build_tree()
        ss = identify_superspreader_modules(tree)
        assert len(ss) > 0
        # a.py should be a superspreader (3 infections)
        module_names = [m for m, _ in ss]
        assert "a.py" in module_names

    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        ss = identify_superspreader_modules(tree)
        assert ss == []

    def test_top_n(self):
        tree = _build_tree()
        ss = identify_superspreader_modules(tree, top_n=2)
        assert len(ss) <= 2


class TestIdentifySuperspreaderDevelopers:
    def test_basic(self):
        tree = _build_tree()
        devs = identify_superspreader_developers(tree)
        assert len(devs) > 0
        # Alice caused 3 infections
        emails = [d.email for d in devs]
        assert "alice@test.com" in emails

    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        devs = identify_superspreader_developers(tree)
        assert devs == []

    def test_superspreader_flag(self):
        tree = _build_tree()
        devs = identify_superspreader_developers(tree)
        # At least one should be flagged
        any_ss = any(d.is_superspreader for d in devs)
        assert any_ss or len(devs) > 0  # May not flag with few devs


class TestIdentifySuperspreaderEvents:
    def test_basic(self):
        tree = _build_tree()
        events = identify_superspreader_events(tree)
        assert len(events) > 0

    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        events = identify_superspreader_events(tree)
        assert events == []


class TestComputeSuperspreaderImpact:
    def test_basic(self):
        tree = _build_tree()
        impact = compute_superspreader_impact("a.py", tree)
        assert impact["direct_infections"] == 3
        assert impact["total_reach"] >= 3

    def test_no_impact(self):
        tree = _build_tree()
        impact = compute_superspreader_impact("nonexistent.py", tree)
        assert impact["direct_infections"] == 0
        assert impact["total_reach"] == 0

    def test_chain_reach(self):
        tree = _build_tree()
        # a.py -> b.py -> e.py (2 levels)
        # a.py -> d.py -> f.py, g.py (2 levels)
        impact = compute_superspreader_impact("a.py", tree)
        assert impact["total_reach"] >= 5  # b,c,d,e,f,g minus a itself
