"""Pattern scanner — detect propagating patterns in source code.

Uses AST matching for Python and regex patterns for all languages.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Optional

from ussy_endemic.models import (
    Compartment,
    Module,
    Pattern,
    PatternType,
)

# Built-in pattern definitions
BUILTIN_PATTERNS: list[dict] = [
    {
        "name": "bare-except",
        "pattern_type": PatternType.BAD,
        "description": "bare except: (swallows errors)",
        "regex_pattern": r"except\s*:",
        "ast_check": "bare_except",
    },
    {
        "name": "broad-except",
        "pattern_type": PatternType.BAD,
        "description": "except Exception (too broad)",
        "regex_pattern": r"except\s+Exception\s*(?:as\s+\w+)?\s*:",
        "ast_check": "broad_except",
    },
    {
        "name": "pass-in-except",
        "pattern_type": PatternType.BAD,
        "description": "except block containing only pass",
        "regex_pattern": r"except\s+[\w.]+\s*(?:as\s+\w+)?\s*:\s*\n\s*pass",
        "ast_check": "pass_in_except",
    },
    {
        "name": "god-class",
        "pattern_type": PatternType.BAD,
        "description": "class with >15 methods",
        "regex_pattern": "",
        "ast_check": "god_class",
    },
    {
        "name": "print-debugging",
        "pattern_type": PatternType.BAD,
        "description": "print() calls in non-test code",
        "regex_pattern": r"^\s*print\s*\(",
        "ast_check": "print_debugging",
    },
    {
        "name": "no-type-hints",
        "pattern_type": PatternType.BAD,
        "description": "functions without type hints",
        "regex_pattern": "",
        "ast_check": "no_type_hints",
    },
    {
        "name": "test-skip-no-reason",
        "pattern_type": PatternType.BAD,
        "description": "@pytest.mark.skip without reason",
        "regex_pattern": r"@pytest\.mark\.skip\s*\(\s*\)",
        "ast_check": "",
    },
    {
        "name": "todo-forever",
        "pattern_type": PatternType.BAD,
        "description": "TODO comments older than 6 months",
        "regex_pattern": r"#\s*TODO",
        "ast_check": "",
    },
    {
        "name": "structured-logging",
        "pattern_type": PatternType.GOOD,
        "description": "Uses structured logging (logging module)",
        "regex_pattern": r"import\s+logging|from\s+logging\s+import",
        "ast_check": "",
    },
    {
        "name": "type-hinted-returns",
        "pattern_type": PatternType.GOOD,
        "description": "Functions with return type hints",
        "regex_pattern": r"def\s+\w+\s*\([^)]*\)\s*->",
        "ast_check": "",
    },
    {
        "name": "custom-exceptions",
        "pattern_type": PatternType.GOOD,
        "description": "Defines custom exception classes",
        "regex_pattern": r"class\s+\w+Error\s*\(\s*\w*Exception",
        "ast_check": "",
    },
]


class ASTChecker:
    """AST-based pattern checking for Python files."""

    @staticmethod
    def bare_except(tree: ast.AST) -> list[int]:
        """Find bare except: lines."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                results.append(node.lineno)
        return results

    @staticmethod
    def broad_except(tree: ast.AST) -> list[int]:
        """Find except Exception: lines."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is not None:
                if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    results.append(node.lineno)
        return results

    @staticmethod
    def pass_in_except(tree: ast.AST) -> list[int]:
        """Find except blocks containing only pass."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if (len(node.body) == 1 and
                        isinstance(node.body[0], ast.Pass)):
                    results.append(node.lineno)
        return results

    @staticmethod
    def god_class(tree: ast.AST, threshold: int = 15) -> list[int]:
        """Find classes with more than threshold methods."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if len(methods) > threshold:
                    results.append(node.lineno)
        return results

    @staticmethod
    def print_debugging(tree: ast.AST) -> list[int]:
        """Find print() calls."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    results.append(node.lineno)
        return results

    @staticmethod
    def no_type_hints(tree: ast.AST) -> list[int]:
        """Find functions without type hints."""
        results = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip dunder methods
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                # Check if return annotation exists
                if node.returns is None:
                    results.append(node.lineno)
        return results


class PatternScanner:
    """Scans source code for propagating patterns."""

    def __init__(self, patterns: Optional[list[Pattern]] = None):
        self.patterns = patterns or self._default_patterns()
        self._ast_checker = ASTChecker()

    def _default_patterns(self) -> list[Pattern]:
        """Create Pattern objects from built-in definitions."""
        result = []
        for pdef in BUILTIN_PATTERNS:
            result.append(Pattern(
                name=pdef["name"],
                pattern_type=pdef["pattern_type"],
                description=pdef["description"],
                regex_pattern=pdef["regex_pattern"],
            ))
        return result

    def scan_file(self, filepath: str) -> dict[str, list[int]]:
        """Scan a single file for all patterns.

        Returns dict mapping pattern name -> list of line numbers.
        """
        results: dict[str, list[int]] = {}
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, IOError):
            return results

        # Determine language
        ext = Path(filepath).suffix
        is_python = ext in (".py", ".pyw")

        for pattern in self.patterns:
            lines = []

            # AST check for Python files
            if is_python:
                ast_check = ""
                for pdef in BUILTIN_PATTERNS:
                    if pdef["name"] == pattern.name:
                        ast_check = pdef.get("ast_check", "")
                        break

                if ast_check:
                    try:
                        tree = ast.parse(content, filename=filepath)
                        checker_method = getattr(self._ast_checker, ast_check, None)
                        if checker_method:
                            lines.extend(checker_method(tree))
                    except SyntaxError:
                        pass

            # Regex check for all files
            if pattern.regex_pattern:
                try:
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern.regex_pattern, line):
                            if i not in lines:
                                lines.append(i)
                except re.error:
                    pass

            if lines:
                results[pattern.name] = sorted(lines)

        return results

    def scan_path(self, path: str) -> dict[str, dict[str, list[int]]]:
        """Scan a file or directory for patterns.

        Returns dict mapping filepath -> {pattern_name -> [lines]}.
        """
        results: dict[str, dict[str, list[int]]] = {}
        p = Path(path)

        if p.is_file():
            file_result = self.scan_file(str(p))
            if file_result:
                results[str(p)] = file_result
        elif p.is_dir():
            for root, dirs, files in os.walk(str(p)):
                # Skip hidden dirs and common non-source dirs
                dirs[:] = [d for d in dirs if not d.startswith(".")
                           and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")]
                for fname in files:
                    # Only scan source files
                    ext = Path(fname).suffix
                    if ext in (".py", ".pyw", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp", ".h"):
                        fpath = os.path.join(root, fname)
                        file_result = self.scan_file(fpath)
                        if file_result:
                            results[fpath] = file_result

        return results

    def build_modules(self, scan_results: dict[str, dict[str, list[int]]],
                      total_modules: Optional[int] = None) -> list[Module]:
        """Build Module objects from scan results."""
        all_pattern_names = set()
        for file_patterns in scan_results.values():
            all_pattern_names.update(file_patterns.keys())

        modules = []
        for filepath, file_patterns in scan_results.items():
            patterns_list = list(file_patterns.keys())
            ext = Path(filepath).suffix
            language_map = {
                ".py": "python", ".pyw": "python",
                ".js": "javascript", ".ts": "typescript",
                ".java": "java", ".go": "go",
                ".rs": "rust", ".rb": "ruby",
                ".c": "c", ".cpp": "cpp", ".h": "c",
            }
            language = language_map.get(ext, "unknown")

            has_bad = any(
                p.name in patterns_list and p.pattern_type == PatternType.BAD
                for p in self.patterns
            )

            compartment = Compartment.INFECTED if has_bad else Compartment.SUSCEPTIBLE

            modules.append(Module(
                path=filepath,
                language=language,
                compartment=compartment,
                patterns=patterns_list,
            ))

        return modules

    def compute_pattern_stats(self, scan_results: dict[str, dict[str, list[int]]],
                              total_modules: int = 0) -> list[Pattern]:
        """Compute prevalence statistics for each pattern."""
        if total_modules == 0:
            total_modules = max(len(scan_results), 1)

        # Count files per pattern
        pattern_counts: dict[str, int] = {}
        for file_patterns in scan_results.values():
            for pname in file_patterns:
                pattern_counts[pname] = pattern_counts.get(pname, 0) + 1

        result = []
        for pattern in self.patterns:
            count = pattern_counts.get(pattern.name, 0)
            # Create a copy with updated counts
            p = Pattern(
                name=pattern.name,
                pattern_type=pattern.pattern_type,
                description=pattern.description,
                regex_pattern=pattern.regex_pattern,
                prevalence_count=count,
                total_modules=total_modules,
            )
            result.append(p)

        return result
