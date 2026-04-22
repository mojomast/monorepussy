"""Error Extractor — Secures the crime scene by isolating errors from noise.

Multi-format log parser that recognizes:
- Compiler errors (Rust, Go, TypeScript, Python, C++)
- Test framework failures (pytest, jest, go test, cargo test)
- Runtime errors (stack traces, panics, OOM, segfaults)
- CI/CD failures (GitHub Actions, GitLab CI, Jenkins)
- Build system errors (cargo, npm, pip, gradle, bazel)

Uses a streaming parser to handle large logs without loading everything into memory.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Iterator, Tuple


@dataclass
class IsolatedError:
    """An error isolated from log noise."""
    line_number: int
    content: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    error_type: str = "unknown"
    language: Optional[str] = None
    file_path: Optional[str] = None
    line_in_file: Optional[int] = None
    severity: str = "error"

    @property
    def full_context(self) -> List[str]:
        """Return all context lines including the error itself."""
        return self.context_before + [self.content] + self.context_after

    def to_dict(self) -> dict:
        return {
            "line_number": self.line_number,
            "content": self.content,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "error_type": self.error_type,
            "language": self.language,
            "file_path": self.file_path,
            "line_in_file": self.line_in_file,
            "severity": self.severity,
        }


# Error pattern definitions: (regex, error_type, language, severity)
ERROR_PATTERNS = [
    # Rust compilation errors
    (r"^error\[E\d+\]:", "rust_compile", "rust", "error"),
    (r"^error: ", "rust_compile", "rust", "error"),
    (r"^error: aborting due to", "rust_compile", "rust", "error"),
    (r"cannot find (?:function|module|struct|enum|type|value|trait|method|field) `", "rust_compile", "rust", "error"),
    (r"mismatched types", "rust_compile", "rust", "error"),
    (r"trait `.*` is not implemented for", "rust_compile", "rust", "error"),

    # Go compilation errors
    (r"^\.\/[^\s]+\.go:\d+:\d+: ", "go_compile", "go", "error"),
    (r"undefined: ", "go_compile", "go", "error"),
    (r"cannot refer to unexported name", "go_compile", "go", "error"),
    (r"imported and not used:", "go_compile", "go", "warning"),

    # TypeScript/JavaScript errors
    (r"error TS\d+:", "typescript_compile", "typescript", "error"),
    (r"TypeError:", "js_runtime", "javascript", "error"),
    (r"ReferenceError:", "js_runtime", "javascript", "error"),
    (r"SyntaxError:", "js_runtime", "javascript", "error"),
    (r"Cannot find module", "js_runtime", "javascript", "error"),
    (r"Module not found: Error:", "js_module", "javascript", "error"),

    # Python errors
    (r"Traceback \(most recent call last\):", "python_traceback", "python", "error"),
    (r"^\w+Error:", "python_error", "python", "error"),
    (r"ImportError:", "python_error", "python", "error"),
    (r"ModuleNotFoundError:", "python_error", "python", "error"),
    (r"SyntaxError:", "python_error", "python", "error"),
    (r"IndentationError:", "python_error", "python", "error"),
    (r"KeyError:", "python_error", "python", "error"),
    (r"AttributeError:", "python_error", "python", "error"),
    (r"TypeError:", "python_error", "python", "error"),
    (r"ValueError:", "python_error", "python", "error"),

    # C/C++ errors
    (r"[^\s]+:\d+:\d+: error:", "cpp_compile", "cpp", "error"),
    (r"undefined reference to ", "cpp_linker", "cpp", "error"),
    (r"fatal error:", "cpp_compile", "cpp", "error"),
    (r"Segmentation fault", "segfault", "cpp", "error"),

    # Test framework failures
    (r"FAILED ", "test_failure", None, "error"),
    (r"FAIL\s+", "test_failure", None, "error"),
    (r"AssertionError", "test_failure", None, "error"),
    (r"--- FAIL:", "go_test_failure", "go", "error"),
    (r"test .+ \.\.\. FAILED", "cargo_test_failure", "rust", "error"),
    (r"✕|✗|✖", "test_failure", None, "error"),
    (r"×\d+ tests? failed", "jest_failure", "javascript", "error"),

    # Runtime errors
    (r"panic: ", "panic", None, "error"),
    (r"Out of memory", "oom", None, "error"),
    (r"Stack Overflow", "stack_overflow", None, "error"),
    (r"SIGSEGV", "segfault", None, "error"),
    (r"SIGKILL", "killed", None, "error"),
    (r"KeyboardInterrupt", "interrupt", None, "warning"),

    # CI/CD failures
    (r"##\[error\]", "github_actions", None, "error"),
    (r"ERROR: Job failed:", "gitlab_ci", None, "error"),
    (r"BUILD FAILED", "ci_build_failure", None, "error"),
    (r"ERROR: Build .* failed", "jenkins", None, "error"),

    # Build system errors
    (r"error: build failed", "cargo_build", "rust", "error"),
    (r"npm ERR! ", "npm_error", "javascript", "error"),
    (r"pip install.*ERROR:", "pip_error", "python", "error"),
    (r"FAILURE: Build failed with an exception", "gradle_error", "java", "error"),
    (r"ERROR: .*BUILD$", "bazel_error", None, "error"),

    # Generic
    (r"^\[ERROR\]", "generic_error", None, "error"),
    (r"^Error: ", "generic_error", None, "error"),
    (r"^FATAL:", "fatal_error", None, "error"),
    (r"Exception:", "exception", None, "error"),
]

# File path extraction patterns
FILE_PATH_PATTERNS = [
    # Rust: src/file.rs:line:col
    (r"([a-zA-Z0-9_./\-]+\.rs):(\d+)(?::(\d+))?", "rust"),
    # Go: ./file.go:line:col
    (r"([a-zA-Z0-9_./\-]+\.go):(\d+)(?::(\d+))?", "go"),
    # Python: File "path/to/file.py", line N
    (r'File "([^"]+\.py)", line (\d+)', "python"),
    # TypeScript/JS: path/to/file.ts:line:col
    (r"([a-zA-Z0-9_./\-]+\.(?:ts|tsx|js|jsx)):(\d+)(?::(\d+))?", "typescript"),
    # C/C++: file.cpp:line:col
    (r"([a-zA-Z0-9_./\-]+\.(?:c|cpp|cc|cxx|h|hpp)):(\d+)(?::(\d+))?", "cpp"),
    # Java: at com.example.Class.method(File.java:123)
    (r"at\s+(?:\w+\.)+\w+\((\w+\.java):(\d+)\)", "java"),
]

# Context size: how many lines before/after an error to capture
DEFAULT_CONTEXT_SIZE = 5


class ErrorExtractor:
    """Extracts errors from log text using pattern matching."""

    def __init__(self, context_size: int = DEFAULT_CONTEXT_SIZE):
        self.context_size = context_size
        self._compiled_patterns = [
            (re.compile(p, re.MULTILINE), etype, lang, sev)
            for p, etype, lang, sev in ERROR_PATTERNS
        ]
        self._compiled_file_patterns = [
            (re.compile(p), lang) for p, lang in FILE_PATH_PATTERNS
        ]

    def extract_file_path(self, line: str, language: Optional[str] = None) -> Tuple[Optional[str], Optional[int]]:
        """Extract file path and line number from an error line."""
        for pattern, lang in self._compiled_file_patterns:
            if language and lang != language:
                continue
            match = pattern.search(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2)) if match.group(2) else None
                return file_path, line_num
        return None, None

    def detect_language(self, line: str) -> Optional[str]:
        """Detect the programming language from an error line."""
        for pattern, etype, lang, sev in self._compiled_patterns:
            if pattern.search(line) and lang:
                return lang
        return None

    def extract_from_text(self, text: str) -> List[IsolatedError]:
        """Extract all errors from a text string."""
        lines = text.splitlines()
        return self._extract_from_lines(lines)

    def extract_from_lines(self, lines: List[str]) -> List[IsolatedError]:
        """Extract all errors from a list of lines."""
        return self._extract_from_lines(lines)

    def _extract_from_lines(self, lines: List[str]) -> List[IsolatedError]:
        """Internal: extract errors from a list of lines."""
        errors = []
        for i, line in enumerate(lines):
            for pattern, error_type, language, severity in self._compiled_patterns:
                if pattern.search(line):
                    context_before = lines[max(0, i - self.context_size):i]
                    context_after = lines[i + 1:min(len(lines), i + 1 + self.context_size)]

                    file_path, line_in_file = self.extract_file_path(line, language)

                    # If not found on the error line, search context
                    if not file_path:
                        for ctx_line in context_before:
                            fp, ln = self.extract_file_path(ctx_line, language)
                            if fp:
                                file_path, line_in_file = fp, ln
                                break

                    error = IsolatedError(
                        line_number=i + 1,
                        content=line,
                        context_before=context_before,
                        context_after=context_after,
                        error_type=error_type,
                        language=language or self.detect_language(line),
                        file_path=file_path,
                        line_in_file=line_in_file,
                        severity=severity,
                    )
                    errors.append(error)
                    break  # Don't match multiple patterns on same line

        return errors

    def stream_extract(self, line_iterator: Iterator[str]) -> Iterator[IsolatedError]:
        """Streaming extraction for large logs. Yields errors as they are found."""
        buffer = []
        for line in line_iterator:
            buffer.append(line.rstrip("\n"))
            # Keep buffer limited for context
            max_buffer = self.context_size * 2 + 1
            if len(buffer) > max_buffer * 2:
                # Check the middle line for errors
                mid = len(buffer) // 2
                self._check_and_yield(buffer, mid)

        # Process remaining buffer
        for i in range(len(buffer)):
            for error in self._check_and_yield_list(buffer, i):
                yield error

    def _check_and_yield(self, buffer: List[str], idx: int) -> Optional[IsolatedError]:
        """Check a single line in buffer and return error if found."""
        line = buffer[idx]
        for pattern, error_type, language, severity in self._compiled_patterns:
            if pattern.search(line):
                start = max(0, idx - self.context_size)
                end = min(len(buffer), idx + 1 + self.context_size)
                return IsolatedError(
                    line_number=idx + 1,
                    content=line,
                    context_before=buffer[start:idx],
                    context_after=buffer[idx + 1:end],
                    error_type=error_type,
                    language=language,
                    severity=severity,
                )
        return None

    def _check_and_yield_list(self, buffer: List[str], idx: int) -> List[IsolatedError]:
        """Check a single line in buffer and return list of errors."""
        result = self._check_and_yield(buffer, idx)
        return [result] if result else []

    def deduplicate(self, errors: List[IsolatedError]) -> List[IsolatedError]:
        """Remove duplicate errors that are close together (same type, nearby lines)."""
        if not errors:
            return []
        deduped = [errors[0]]
        for err in errors[1:]:
            last = deduped[-1]
            if err.error_type == last.error_type and abs(err.line_number - last.line_number) <= 2:
                # Keep the one with more context
                if len(err.full_context) > len(last.full_context):
                    deduped[-1] = err
            else:
                deduped.append(err)
        return deduped
