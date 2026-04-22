"""AST-based assertion quality analyzer for hooch detection."""

from __future__ import annotations

import ast
from typing import Optional


# Patterns that indicate trivial/stale assertions
TRIVIAL_ASSERTION_PATTERNS = {
    "assert_true": "assert True",
    "assert_not_none_only": "assert ... is not None",
    "assert_equals_self": "assert x == x",
    "assert_type_only": "assert isinstance(x, type) without deeper check",
    "assert_len_gt_zero": "assert len(x) > 0",
    "assert_bool": "assert x (bare truthiness)",
}


def analyze_assertion_quality(source_code: str) -> dict[str, float]:
    """Analyze the quality of assertions in a test function or module.

    Returns a dict with:
      - score: 0-1 overall assertion quality (1 = excellent, 0 = trivial)
      - has_trivial: bool
      - assertion_count: int
      - trivial_count: int
      - issues: list of description strings
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return {
            "score": 0.5,
            "has_trivial": False,
            "assertion_count": 0,
            "trivial_count": 0,
            "issues": ["Could not parse source"],
        }

    assertions = []
    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            assertions.append(node)
            trivial = _check_trivial_assertion(node)
            if trivial:
                issues.append(trivial)

    assertion_count = len(assertions)
    trivial_count = len(issues)

    if assertion_count == 0:
        return {
            "score": 0.0,
            "has_trivial": True,
            "assertion_count": 0,
            "trivial_count": 0,
            "issues": ["No assertions found"],
        }

    # Score: ratio of non-trivial assertions, penalized for trivial ones
    non_trivial = assertion_count - trivial_count
    score = non_trivial / assertion_count if assertion_count > 0 else 0.0

    # Bonus for having specific comparisons (==, !=, <, >) vs bare truthiness
    for node in assertions:
        if _has_specific_comparison(node):
            score = min(1.0, score + 0.05)

    return {
        "score": round(min(1.0, max(0.0, score)), 3),
        "has_trivial": trivial_count > 0,
        "assertion_count": assertion_count,
        "trivial_count": trivial_count,
        "issues": issues,
    }


def _check_trivial_assertion(node: ast.Assert) -> Optional[str]:
    """Check if an assertion is trivial. Returns issue description or None."""
    test = node.test

    # assert True
    if isinstance(test, ast.Constant) and test.value is True:
        return TRIVIAL_ASSERTION_PATTERNS["assert_true"]

    # assert ... is not None (without further checks)
    if isinstance(test, ast.Compare):
        # Check for `is not None` only
        if len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot):
            if len(test.comparators) == 1:
                comp = test.comparators[0]
                if isinstance(comp, ast.Constant) and comp.value is None:
                    # This is `assert x is not None` - trivial if it's the only check
                    return TRIVIAL_ASSERTION_PATTERNS["assert_not_none_only"]

        # Check for self-comparison: assert x == x
        if len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
            if len(test.comparators) == 1:
                if _ast_equal(test.left, test.comparators[0]):
                    return TRIVIAL_ASSERTION_PATTERNS["assert_equals_self"]

    # assert isinstance(x, SomeType) only
    if isinstance(test, ast.Call):
        if isinstance(test.func, ast.Name) and test.func.id == "isinstance":
            return TRIVIAL_ASSERTION_PATTERNS["assert_type_only"]

    return None


def _has_specific_comparison(node: ast.Assert) -> bool:
    """Check if assertion has a specific value comparison."""
    test = node.test
    if isinstance(test, ast.Compare):
        for op in test.ops:
            if isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn)):
                return True
    return False


def _ast_equal(a: ast.AST, b: ast.AST) -> bool:
    """Simple structural equality check for AST nodes."""
    if type(a) != type(b):
        return False
    if isinstance(a, ast.Name) and isinstance(b, ast.Name):
        return a.id == b.id
    if isinstance(a, ast.Constant) and isinstance(b, ast.Constant):
        return a.value == b.value
    return False


def check_skip_staleness(source_code: str, skip_threshold_days: float = 90) -> dict:
    """Check for stale skip/xfail decorators.

    Returns info about skip/xfail usage.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return {"has_skip": False, "has_xfail": False, "skip_reasons": [], "xfail_reasons": []}

    skip_reasons = []
    xfail_reasons = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                dec_name = _get_decorator_name(decorator)
                if dec_name and "skip" in dec_name.lower():
                    reason = _get_decorator_reason(decorator)
                    skip_reasons.append({"function": node.name, "reason": reason})
                elif dec_name and "xfail" in dec_name.lower():
                    reason = _get_decorator_reason(decorator)
                    xfail_reasons.append({"function": node.name, "reason": reason})

    return {
        "has_skip": len(skip_reasons) > 0,
        "has_xfail": len(xfail_reasons) > 0,
        "skip_reasons": skip_reasons,
        "xfail_reasons": xfail_reasons,
    }


def _get_decorator_name(decorator: ast.expr) -> Optional[str]:
    """Extract decorator name."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        if isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    return None


def _get_decorator_reason(decorator: ast.expr) -> str:
    """Extract reason from decorator call."""
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if keyword.arg == "reason":
                if isinstance(keyword.value, ast.Constant):
                    return str(keyword.value.value)
        # Check positional args (second arg is often reason)
        if len(decorator.args) >= 2:
            if isinstance(decorator.args[1], ast.Constant):
                return str(decorator.args[1].value)
    return ""
