"""Tests for the Syntrop analyzer module."""

import pytest
from pathlib import Path

from ussy_syntrop.analyzer import (
    AssumptionScanner,
    BehavioralAssumption,
    scan_source,
    scan_file,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestBehavioralAssumption:
    """Tests for BehavioralAssumption dataclass."""

    def test_create_assumption(self):
        a = BehavioralAssumption(
            kind="iteration-order",
            description="Test",
            line=5,
        )
        assert a.kind == "iteration-order"
        assert a.line == 5
        assert a.severity == "warning"
        assert a.related_probes == []

    def test_assumption_with_all_fields(self):
        a = BehavioralAssumption(
            kind="eval-order",
            description="Test description",
            line=10,
            col=4,
            code_snippet="f(a, b)",
            severity="error",
            related_probes=["shuffle-evaluation-order"],
        )
        assert a.code_snippet == "f(a, b)"
        assert a.severity == "error"


class TestAssumptionScanner:
    """Tests for the AssumptionScanner AST visitor."""

    def test_detect_dict_iteration(self):
        source = """
for key in d.keys():
    print(key)
"""
        assumptions = scan_source(source)
        assert any(a.kind == "iteration-order" for a in assumptions)

    def test_detect_dict_constructor_iteration(self):
        source = """
for item in dict(data):
    pass
"""
        assumptions = scan_source(source)
        assert any(a.kind == "iteration-order" for a in assumptions)

    def test_detect_set_iteration(self):
        source = """
for item in set(items):
    pass
"""
        assumptions = scan_source(source)
        assert any(a.kind == "iteration-order" for a in assumptions)

    def test_detect_multi_arg_function_call(self):
        source = """
result = f(a, b, c)
"""
        assumptions = scan_source(source)
        assert any(a.kind == "eval-order" for a in assumptions)

    def test_detect_single_arg_no_eval_order(self):
        source = """
result = f(a)
"""
        assumptions = scan_source(source)
        eval_order = [a for a in assumptions if a.kind == "eval-order"]
        assert len(eval_order) == 0

    def test_detect_augmented_assignment(self):
        source = """
x += 1
"""
        assumptions = scan_source(source)
        assert any(a.kind == "timing-atomicity" for a in assumptions)

    def test_detect_chained_comparison(self):
        source = """
if 0 < x < 10:
    pass
"""
        assumptions = scan_source(source)
        assert any(a.kind == "eval-order" for a in assumptions)

    def test_detect_multiple_assignment_targets(self):
        source = """
a = b = expr()
"""
        assumptions = scan_source(source)
        assert any(a.kind == "state-aliasing" for a in assumptions)

    def test_detect_dict_literal_duplicate_keys(self):
        source = """
d = {"a": 1, "a": 2}
"""
        assumptions = scan_source(source)
        assert any(a.kind == "state-aliasing" for a in assumptions)

    def test_detect_list_comprehension(self):
        source = """
result = [x for x in items]
"""
        assumptions = scan_source(source)
        assert any(a.kind == "iteration-order" for a in assumptions)

    def test_detect_modification_during_iteration(self):
        source = """
for item in items:
    items.append(item)
"""
        assumptions = scan_source(source)
        assert any(a.kind == "state-mutation-during-iteration" for a in assumptions)

    def test_no_assumptions_in_pure_code(self):
        source = """
def add(a, b):
    return a + b
"""
        assumptions = scan_source(source)
        # This should have minimal or no assumptions
        # (the function call with 2 args would trigger eval-order)
        # Let's check there's nothing serious
        serious = [a for a in assumptions if a.severity in ("warning", "error")]
        assert len(serious) == 0

    def test_syntax_error_returns_empty(self):
        source = "def broken(:"
        assumptions = scan_source(source)
        assert assumptions == []

    def test_empty_source(self):
        assumptions = scan_source("")
        assert assumptions == []

    def test_related_probes_populated(self):
        source = """
for key in d.keys():
    pass
"""
        assumptions = scan_source(source)
        iter_assumptions = [a for a in assumptions if a.kind == "iteration-order"]
        assert len(iter_assumptions) > 0
        assert "randomize-iteration" in iter_assumptions[0].related_probes

    def test_code_snippet_populated(self):
        source = """
x += 1
"""
        assumptions = scan_source(source)
        assert len(assumptions) > 0
        assert assumptions[0].code_snippet != ""

    def test_sorted_iteration(self):
        source = """
for item in sorted(items):
    pass
"""
        assumptions = scan_source(source)
        assert any(a.kind == "iteration-order" for a in assumptions)


class TestScanFile:
    """Tests for scanning files."""

    def test_scan_fixture_file(self):
        fixture = FIXTURES_DIR / "iteration_order.py"
        if fixture.exists():
            assumptions = scan_file(str(fixture))
            assert len(assumptions) > 0

    def test_scan_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            scan_file("/nonexistent/file.py")

    def test_scan_clean_fixture(self):
        fixture = FIXTURES_DIR / "clean.py"
        if fixture.exists():
            assumptions = scan_file(str(fixture))
            # Clean code should have fewer assumptions
            # but may still trigger on multi-arg calls
            serious = [a for a in assumptions if a.severity in ("warning", "error")]
            assert len(serious) == 0
