"""Pattern Matcher — Matches extracted errors against known error patterns.

Uses a SQLite-backed pattern database with curated error patterns per
language/framework. Supports custom project-specific patterns.
"""

import re
import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import ErrorPattern, VictimType


# Default database location
DEFAULT_DB_PATH = Path(__file__).parent / "data" / "patterns.db"

# Seed patterns for initial database population
SEED_PATTERNS = [
    # Rust patterns
    ("rust_compile", "rust", r"trait `(\w+)` is not implemented for `(\w+)`",
     "Missing trait implementation: {1} needs to implement {0}",
     "Add `impl {0} for {1} {{ ... }}` or use a type that already implements {0}",
     0.92),
    ("rust_compile", "rust", r"cannot find (?:function|module|struct|enum|type|value|trait|method|field) `(\w+)`",
     "The name `{0}` is not defined in the current scope",
     "Check spelling, import the item, or define it. Add `use path::to::{0};` if it exists elsewhere",
     0.88),
    ("rust_compile", "rust", r"mismatched types.*expected `(\w+)`.*found `(\w+)`",
     "Type mismatch: expected {0}, found {1}",
     "Convert the value with `.into()`, `.to_{0}()`, or change the function signature",
     0.85),
    ("rust_compile", "rust", r"borrow of moved value: `(\w+)`",
     "Value `{0}` was moved and then used again",
     "Clone the value before moving (`.clone()`) or use a reference (`&{0}`)",
     0.87),
    ("rust_compile", "rust", r"cannot borrow `(\w+)` as mutable",
     "Attempted to mutate an immutable reference",
     "Make the binding mutable with `let mut {0}` or use interior mutability (RefCell)",
     0.83),

    # Go patterns
    ("go_compile", "go", r"undefined: (\w+)",
     "Name `{0}` is not defined — missing import or typo",
     "Add the missing import or check spelling. If it's from another package, use `import \"path/to/pkg\"`",
     0.90),
    ("go_compile", "go", r"cannot refer to unexported name (\w+)\.(\w+)",
     "Attempted to use unexported (private) name {0}.{1}",
     "Use the exported version (capitalize first letter: {0}.{1_cap}) or access through a public method",
     0.85),
    ("go_compile", "go", r"imported and not used: \"([^\"]+)\"",
     "Package `{0}` is imported but never used",
     "Remove the unused import or prefix with underscore: `_ \"{0}\"`",
     0.95),
    ("go_compile", "go", r"(\w+) declared (?:but not used|and not used)",
     "Variable `{0}` is declared but never used",
     "Remove the unused variable or use `_ = {0}` to silence the error",
     0.93),

    # Python patterns
    ("python_error", "python", r"ModuleNotFoundError: No module named '(\w+)'",
     "Python module `{0}` is not installed",
     "Install it: `pip install {0}` or add to requirements.txt",
     0.95),
    ("python_error", "python", r"ImportError: cannot import name '(\w+)' from '(\w+)'",
     "Name `{0}` does not exist in module `{1}`",
     "Check spelling of `{0}`. It may have been removed or renamed in your version of {1}",
     0.85),
    ("python_error", "python", r"SyntaxError: invalid syntax",
     "Python syntax error — the parser hit something unexpected",
     "Check for missing colons, mismatched parentheses, or invalid characters. Often on the line BEFORE the reported line",
     0.70),
    ("python_error", "python", r"SyntaxError: EOL while scanning string literal",
     "Unterminated string — missing closing quote",
     "Add the missing closing quote (single or double) to the string",
     0.92),
    ("python_error", "python", r"IndentationError: (?:unexpected indent|expected an indented block)",
     "Incorrect indentation in Python code",
     "Check for mixed tabs and spaces (use consistent 4-space indentation). Ensure code blocks after colons are indented",
     0.88),
    ("python_error", "python", r"KeyError: '(\w+)'",
     "Dictionary key `{0}` does not exist",
     "Use `.get('{0}', default)` for safe access, or check if key exists with `'{0}' in dict`",
     0.87),
    ("python_error", "python", r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
     "Object of type `{0}` has no attribute `{1}`",
     "Check spelling of `{1}`. Verify the object type — it may not be what you expect. Print `type(obj)` to confirm",
     0.82),
    ("python_error", "python", r"TypeError: '(\w+)' object is not (?:callable|subscriptable|iterable)",
     "Using `{0}` object incorrectly — it doesn't support this operation",
     "Check that you're not treating a {0} as a function/list/dict. May need to call a method instead",
     0.80),
    ("python_error", "python", r"ValueError: (?:invalid literal|could not convert)",
     "Cannot convert a value to the expected type",
     "Validate input before conversion. Use try/except around int()/float()/etc.",
     0.78),
    ("python_error", "python", r"RecursionError: maximum recursion depth exceeded",
     "Infinite recursion — a function is calling itself without a base case",
     "Add a base case to stop recursion, or use iteration instead. Set `sys.setrecursionlimit()` as a last resort",
     0.90),
    ("python_error", "python", r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'",
     "File `{0}` does not exist",
     "Check the file path. Use `Path('{0}').exists()` before opening. May need to create the file first",
     0.92),
    ("python_error", "python", r"PermissionError: \[Errno 13\] Permission denied: '([^']+)'",
     "No permission to access `{0}`",
     "Check file permissions: `chmod` on Unix. May need to run with elevated privileges or check ownership",
     0.88),

    # TypeScript/JavaScript patterns
    ("typescript_compile", "typescript", r"error TS230[45]: Cannot find (?:module|name) '([^']+)'",
     "TypeScript cannot find `{0}`",
     "Install the package (`npm install {0}`) and/or add type declarations (`npm install @types/{0}`)",
     0.90),
    ("typescript_compile", "typescript", r"error TS2322: Type '([^']+)' is not assignable to type '([^']+)'",
     "Type mismatch: cannot assign {0} to {1}",
     "Add a type assertion (`as {1}`), fix the source type, or update the target type definition",
     0.82),
    ("typescript_compile", "typescript", r"error TS2345: Argument of type '([^']+)' is not assignable",
     "Wrong argument type passed to function",
     "Check the function signature and ensure arguments match expected types",
     0.80),
    ("js_runtime", "javascript", r"TypeError: Cannot read propert(?:y|ies) of (?:undefined|null) \(reading '(\w+)'\)",
     "Attempted to access property `{0}` on null/undefined",
     "Add null checks: `obj?.{0}` or `if (obj) obj.{0}`. The object may not be initialized",
     0.93),
    ("js_runtime", "javascript", r"TypeError: (\w+) is not a function",
     "Called `{0}()` on something that isn't a function",
     "Check that {0} is defined and is callable. May be undefined, null, or wrong type",
     0.85),
    ("js_module", "javascript", r"Cannot find module '([^']+)'",
     "Module `{0}` cannot be resolved",
     "Install it: `npm install {0}`. Check the import path and module name spelling",
     0.90),
    ("js_module", "javascript", r"Module not found: Error: Can't resolve '([^']+)'",
     "Webpack/bundler cannot resolve module `{0}`",
     "Install the package (`npm install {0}`) or check the import path",
     0.88),

    # C/C++ patterns
    ("cpp_compile", "cpp", r"undefined reference to `(\w+)'",
     "Linker error: function `{0}` is declared but not defined",
     "Add the implementation for `{0}`, link the correct library, or add the source file to the build",
     0.87),
    ("cpp_compile", "cpp", r"fatal error: (\w+\.h): No such file or directory",
     "Header file `{0}` not found",
     "Install the development package or add the include path: `-I/path/to/headers`",
     0.88),

    # Test framework patterns
    ("test_failure", None, r"AssertionError: (.+)",
     "Test assertion failed: {0}",
     "Check the test's expected vs actual values. The assertion message explains what was expected",
     0.80),
    ("test_failure", None, r"(\d+) failed",
     "{0} test(s) failed",
     "Review the individual test failures above for specific causes",
     0.70),

    # CI/CD patterns
    ("github_actions", None, r"##\[error\](.+)",
     "GitHub Actions error: {0}",
     "Check the workflow file and the step that produced this error",
     0.75),
    ("npm_error", "javascript", r"npm ERR! (.+)",
     "npm error: {0}",
     "Check package.json and npm configuration. Try deleting node_modules and reinstalling",
     0.65),
    ("pip_error", "python", r"ERROR: Could not find a version that satisfies the requirement (\S+)",
     "Package `{0}` not found on PyPI",
     "Check the package name spelling. It may not exist or may have been removed from PyPI",
     0.90),
    ("pip_error", "python", r"ERROR: No matching distribution found for (\S+)",
     "No compatible version of `{0}` available for this Python/platform",
     "Check Python version compatibility. Try `pip install {0} --no-deps` or a specific version",
     0.85),

    # Runtime patterns
    ("oom", None, r"Out of memory",
     "Process ran out of memory",
     "Reduce data size, use streaming/chunked processing, or increase available memory",
     0.88),
    ("segfault", None, r"Segmentation fault",
     "Segfault — invalid memory access",
     "Check for null pointer dereference, buffer overflows, or use-after-free bugs. Run with a sanitizer",
     0.65),
    ("panic", None, r"panic: (.+)",
     "Runtime panic: {0}",
     "The program hit an unrecoverable condition. Check the panic message for the root cause",
     0.75),
]


class PatternMatcher:
    """Matches errors against a database of known patterns."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._ensure_database()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_database(self):
        """Create the database and seed patterns if they don't exist."""
        conn = self.conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                language TEXT,
                pattern_regex TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                fix_template TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5,
                is_custom INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_type
            ON error_patterns(pattern_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_language
            ON error_patterns(language)
        """)

        # Seed patterns only if database is empty
        count = conn.execute("SELECT COUNT(*) FROM error_patterns").fetchone()[0]
        if count == 0:
            for ptype, lang, regex, root_cause, fix, conf in SEED_PATTERNS:
                conn.execute(
                    "INSERT INTO error_patterns (pattern_type, language, pattern_regex, root_cause, fix_template, confidence) VALUES (?, ?, ?, ?, ?, ?)",
                    (ptype, lang, regex, root_cause, fix, conf)
                )
            conn.commit()

    def match(self, error_content: str, error_type: str = None,
              language: str = None) -> Optional[ErrorPattern]:
        """Match an error against the pattern database."""
        conn = self.conn

        # Build query
        query = "SELECT * FROM error_patterns WHERE 1=1"
        params = []
        if error_type:
            query += " AND pattern_type = ?"
            params.append(error_type)
        if language:
            query += " AND (language = ? OR language IS NULL)"
            params.append(language)
        query += " ORDER BY confidence DESC"

        rows = conn.execute(query, params).fetchall()

        best_match = None
        best_confidence = 0.0

        for row in rows:
            try:
                compiled = re.compile(row["pattern_regex"], re.MULTILINE)
                match = compiled.search(error_content)
                if match:
                    # Compute effective confidence
                    base_conf = row["confidence"]
                    # Boost if language matches
                    if language and row["language"] == language:
                        base_conf *= 1.1
                    # Boost if error_type matches
                    if error_type and row["pattern_type"] == error_type:
                        base_conf *= 1.05

                    effective_conf = min(base_conf, 1.0)

                    if effective_conf > best_confidence:
                        # Format root_cause and fix_template with captured groups
                        try:
                            groups = match.groups() or ()
                            root_cause = row["root_cause"].format(*groups)
                            fix_template = row["fix_template"]
                            # Handle special format strings like {1_cap}
                            if "_cap" in fix_template:
                                for i, g in enumerate(groups):
                                    fix_template = fix_template.replace(
                                        f"{{{i}_cap}}", g.capitalize()
                                    )
                            fix_template = fix_template.format(*groups)
                        except (IndexError, KeyError):
                            root_cause = row["root_cause"]
                            fix_template = row["fix_template"]

                        best_match = ErrorPattern(
                            pattern_type=row["pattern_type"],
                            language=row["language"],
                            root_cause=root_cause,
                            fix_template=fix_template,
                            confidence=round(effective_conf, 2),
                            matched_text=match.group(0),
                        )
                        best_confidence = effective_conf
            except re.error:
                continue

        return best_match

    def add_pattern(self, pattern_type: str, language: Optional[str],
                    regex: str, root_cause: str, fix_template: str,
                    confidence: float = 0.7) -> int:
        """Add a custom error pattern to the database."""
        # Validate regex
        try:
            re.compile(regex)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        cursor = self.conn.execute(
            """INSERT INTO error_patterns
               (pattern_type, language, pattern_regex, root_cause, fix_template, confidence, is_custom)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (pattern_type, language, regex, root_cause, fix_template, confidence)
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_patterns(self, pattern_type: str = None,
                      language: str = None) -> List[dict]:
        """List patterns in the database, optionally filtered."""
        query = "SELECT * FROM error_patterns WHERE 1=1"
        params = []
        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        if language:
            query += " AND language = ?"
            params.append(language)
        query += " ORDER BY confidence DESC"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def remove_pattern(self, pattern_id: int) -> bool:
        """Remove a custom pattern by ID."""
        cursor = self.conn.execute(
            "DELETE FROM error_patterns WHERE id = ? AND is_custom = 1",
            (pattern_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def pattern_count(self) -> int:
        """Return total number of patterns."""
        return self.conn.execute("SELECT COUNT(*) FROM error_patterns").fetchone()[0]

    def classify_victim(self, error_type: str) -> VictimType:
        """Determine what kind of thing failed based on error type."""
        mapping = {
            "rust_compile": VictimType.BUILD,
            "go_compile": VictimType.BUILD,
            "typescript_compile": VictimType.BUILD,
            "cpp_compile": VictimType.BUILD,
            "cpp_linker": VictimType.BUILD,
            "cargo_build": VictimType.BUILD,
            "npm_error": VictimType.BUILD,
            "pip_error": VictimType.BUILD,
            "gradle_error": VictimType.BUILD,
            "bazel_error": VictimType.BUILD,
            "test_failure": VictimType.TEST,
            "cargo_test_failure": VictimType.TEST,
            "go_test_failure": VictimType.TEST,
            "jest_failure": VictimType.TEST,
            "python_traceback": VictimType.RUNTIME,
            "python_error": VictimType.RUNTIME,
            "js_runtime": VictimType.RUNTIME,
            "panic": VictimType.RUNTIME,
            "oom": VictimType.RUNTIME,
            "segfault": VictimType.RUNTIME,
            "stack_overflow": VictimType.RUNTIME,
            "github_actions": VictimType.DEPLOYMENT,
            "gitlab_ci": VictimType.DEPLOYMENT,
            "jenkins": VictimType.DEPLOYMENT,
            "ci_build_failure": VictimType.DEPLOYMENT,
        }
        return mapping.get(error_type, VictimType.UNKNOWN)

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
