"""Stress testing engine — verifies that golden joints' repairs are still load-bearing.

Uses AST manipulation to temporarily comment out repair lines, runs referenced tests,
and records whether the repair is still necessary (solid_gold) or redundant (hollow).

AST node support in LineCommenter
----------------------------------
The following statement types are handled via AST manipulation (``ast.unparse`` is used
to regenerate source, which requires Python 3.9+):

* ``Expr``        — bare expression statements
* ``Assign``      — simple assignment (``x = 1``)
* ``AugAssign``   — augmented assignment (``x += 1``)
* ``AnnAssign``   — annotated assignment (``x: int = 1``)
* ``Delete``      — del statement (``del x``)
* ``Return``      — return statement
* ``Raise``       — raise statement
* ``Assert``      — assert statement
* ``If``          — if block (the *entire* block is replaced with ``pass``, which may
                   silence more code than just the first line — this is intentional)
* ``For``         — for loop (entire block replaced with ``pass``)
* ``While``       — while loop (entire block replaced with ``pass``)
* ``With``        — with statement (entire block replaced with ``pass``)
* ``AsyncWith``   — async with statement (entire block replaced with ``pass``)
* ``Try``         — try/except block (entire block replaced with ``pass``)
* ``FunctionDef`` / ``AsyncFunctionDef`` — traversed so that statements *inside*
                   functions and async functions are reachable

If the target line is not matched by any of the above visitors (e.g. a decorator line,
or a line inside an f-string), ``LineCommenter.found`` remains ``False`` and
``comment_out_line`` falls back to text-based commenting.  Pass ``no_ast=True`` to
``comment_out_line`` (or use ``kintsugi stress --no-ast``) to skip AST manipulation
entirely and always use the text-based fallback.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from .joint import Joint, JointStore


@dataclass
class StressResult:
    """Result of stress-testing a single joint."""

    joint_id: str = ""
    file: str = ""
    line: int = 0
    test_ref: str = ""
    outcome: str = "untested"  # solid_gold | hollow | error | untested
    message: str = ""
    timestamp: str = ""


@dataclass
class StressReport:
    """Report of stress-testing all joints."""

    results: List[StressResult] = field(default_factory=list)

    @property
    def solid_count(self) -> int:
        return sum(1 for r in self.results if r.outcome == "solid_gold")

    @property
    def hollow_count(self) -> int:
        return sum(1 for r in self.results if r.outcome == "hollow")

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.outcome == "error")

    @property
    def untested_count(self) -> int:
        return sum(1 for r in self.results if r.outcome == "untested")

    @property
    def total(self) -> int:
        return len(self.results)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "solid_gold": self.solid_count,
            "hollow": self.hollow_count,
            "error": self.error_count,
            "untested": self.untested_count,
            "results": [
                {
                    "joint_id": r.joint_id,
                    "file": r.file,
                    "line": r.line,
                    "test_ref": r.test_ref,
                    "outcome": r.outcome,
                    "message": r.message,
                    "timestamp": r.timestamp,
                }
                for r in self.results
            ],
        }


class LineCommenter(ast.NodeTransformer):
    """AST transformer that comments out a specific line by replacing its
    statement with a pass statement."""

    def __init__(self, target_line: int):
        self.target_line = target_line
        self.found = False

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        return node

    def _comment_out_line(self, node):
        """If the node is on the target line, replace it with pass + comment."""
        if hasattr(node, "lineno") and node.lineno == self.target_line:
            self.found = True
            # Replace with pass (effectively a no-op)
            new_node = ast.Pass()
            ast.copy_location(new_node, node)
            return new_node
        return node

    def visit_Expr(self, node):
        return self._comment_out_line(node)

    def visit_Assign(self, node):
        return self._comment_out_line(node)

    def visit_AugAssign(self, node):
        return self._comment_out_line(node)

    def visit_AnnAssign(self, node):
        return self._comment_out_line(node)

    def visit_Delete(self, node):
        return self._comment_out_line(node)

    def visit_Return(self, node):
        return self._comment_out_line(node)

    def visit_If(self, node):
        return self._comment_out_line(node)

    def visit_For(self, node):
        return self._comment_out_line(node)

    def visit_While(self, node):
        return self._comment_out_line(node)

    def visit_With(self, node):
        return self._comment_out_line(node)

    def visit_AsyncWith(self, node):
        return self._comment_out_line(node)

    def visit_Try(self, node):
        return self._comment_out_line(node)

    def visit_Raise(self, node):
        return self._comment_out_line(node)

    def visit_Assert(self, node):
        return self._comment_out_line(node)


def comment_out_line(source: str, line_number: int, no_ast: bool = False) -> Tuple[str, bool]:
    """Comment out a specific line in Python source code using AST manipulation.

    Args:
        source: Python source code.
        line_number: 1-indexed line number to comment out.
        no_ast: When True, skip AST manipulation and use text-based commenting directly.

    Returns:
        Tuple of (modified_source, found_line).
    """
    if not no_ast:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # If we can't parse, fall back to text-based commenting
            lines = source.splitlines(keepends=True)
            if 1 <= line_number <= len(lines):
                lines[line_number - 1] = f"# KINTSUGI_REMOVED: {lines[line_number - 1].lstrip('# ')}"
                return "".join(lines), True
            return source, False

        commenter = LineCommenter(line_number)
        modified_tree = commenter.visit(tree)

        if commenter.found:
            try:
                modified_source = ast.unparse(modified_tree)
                return modified_source, True
            except Exception:
                pass  # fall through to text-based fallback

    # Text-based fallback (used when no_ast=True, AST match not found, or ast.unparse fails)
    lines = source.splitlines(keepends=True)
    if 1 <= line_number <= len(lines):
        original = lines[line_number - 1].lstrip()
        indent = lines[line_number - 1][: len(lines[line_number - 1]) - len(original)]
        lines[line_number - 1] = f"{indent}# KINTSUGI_REMOVED: {original}"
        return "".join(lines), True
    return source, False


def run_test(test_ref: str, project_root: Optional[str] = None) -> Tuple[bool, str]:
    """Run a specific test using pytest subprocess.

    Args:
        test_ref: Test name (e.g., 'test_oauth_null_email_crash').
        project_root: Root directory of the project.

    Returns:
        Tuple of (passed, output).
    """
    root = project_root or os.getcwd()
    cmd = [sys.executable, "-m", "pytest", test_ref, "-x", "--tb=short", "-q"]

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 60 seconds"
    except FileNotFoundError:
        return False, "pytest not found — install pytest to use stress testing"
    except Exception as e:
        return False, f"Error running test: {e}"


def stress_test_joint(
    joint: Joint,
    project_root: Optional[str] = None,
    no_ast: bool = False,
) -> StressResult:
    """Stress-test a single joint by temporarily removing its repair and running the test.

    Args:
        joint: The golden joint to test.
        project_root: Root directory of the project.
        no_ast: When True, skip AST manipulation and use text-based commenting directly.

    Returns:
        StressResult indicating whether the joint is solid_gold or hollow.
    """
    now = datetime.now(timezone.utc).isoformat()
    result = StressResult(
        joint_id=joint.id,
        file=joint.file,
        line=joint.line,
        test_ref=joint.test_ref,
        timestamp=now,
    )

    if not joint.test_ref:
        result.outcome = "untested"
        result.message = "No test reference — cannot stress test"
        return result

    if not joint.file:
        result.outcome = "error"
        result.message = "No file specified in joint"
        return result

    root = project_root or os.getcwd()
    file_path = Path(root) / joint.file

    if not file_path.exists():
        result.outcome = "error"
        result.message = f"File not found: {joint.file}"
        return result

    try:
        original_source = file_path.read_text(encoding="utf-8")
    except Exception as e:
        result.outcome = "error"
        result.message = f"Error reading file: {e}"
        return result

    # Comment out the repair line
    modified_source, found = comment_out_line(original_source, joint.line, no_ast=no_ast)

    if not found:
        result.outcome = "error"
        result.message = f"Could not find line {joint.line} in {joint.file}"
        return result

    # Write modified source temporarily
    try:
        file_path.write_text(modified_source, encoding="utf-8")

        # Run the test
        passed, output = run_test(joint.test_ref, root)

        if passed:
            result.outcome = "hollow"
            result.message = "Test PASSED without repair — joint is hollow (repair may be redundant)"
        else:
            result.outcome = "solid_gold"
            result.message = "Test FAILED without repair — joint is solid gold (repair still load-bearing)"

    except Exception as e:
        result.outcome = "error"
        result.message = f"Error during stress test: {e}"
    finally:
        # Always restore the original source
        try:
            file_path.write_text(original_source, encoding="utf-8")
        except Exception:
            pass

    return result


def stress_test_all(
    root: Optional[str] = None,
    junit_output: Optional[str] = None,
    no_ast: bool = False,
) -> StressReport:
    """Stress-test all joints in the store.

    Args:
        root: Repository root path.
        junit_output: Optional path to write JUnit XML output.
        no_ast: When True, skip AST manipulation and use text-based commenting directly.

    Returns:
        StressReport with results for all joints.
    """
    store = JointStore(root)
    joints = store.load_all()
    report = StressReport()

    for joint in joints:
        result = stress_test_joint(joint, root, no_ast=no_ast)
        report.results.append(result)

        # Update joint status in store
        if result.outcome in ("solid_gold", "hollow"):
            store.update(
                joint.id,
                status=result.outcome,
                last_stress_tested=result.timestamp,
            )

    if junit_output:
        write_junit_xml(report, junit_output)

    return report


def write_junit_xml(report: StressReport, output_path: str) -> None:
    """Write stress test results in JUnit XML format."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuite name="kintsugi-stress" tests="{report.total}" '
        f'failures="{report.hollow_count}" errors="{report.error_count}">',
    ]

    for r in report.results:
        classname = r.file.replace("/", ".").replace("\\", ".").replace(".py", "")
        lines.append(
            f'  <testcase classname="{classname}" name="{r.joint_id}" '
            f'file="{r.file}" line="{r.line}">'
        )
        if r.outcome == "hollow":
            lines.append(
                f'    <failure message="Hollow joint: {r.message}">'
                f'{r.message}</failure>'
            )
        elif r.outcome == "error":
            lines.append(f'    <error message="{r.message}">{r.message}</error>')
        elif r.outcome == "untested":
            lines.append(f'    <skipped message="{r.message}"/>')
        lines.append("  </testcase>")

    lines.append("</testsuite>")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
