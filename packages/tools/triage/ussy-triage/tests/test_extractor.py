"""Tests for the ErrorExtractor module."""

import pytest
from ussy_triage.extractor import ErrorExtractor, IsolatedError


class TestIsolatedError:
    """Tests for the IsolatedError data model."""

    def test_basic_creation(self):
        err = IsolatedError(line_number=1, content="Error: something")
        assert err.line_number == 1
        assert err.content == "Error: something"
        assert err.error_type == "unknown"
        assert err.language is None
        assert err.file_path is None
        assert err.line_in_file is None
        assert err.severity == "error"
        assert err.context_before == []
        assert err.context_after == []

    def test_full_creation(self):
        err = IsolatedError(
            line_number=42,
            content="TypeError: cannot read property",
            context_before=["line 40", "line 41"],
            context_after=["line 43", "line 44"],
            error_type="js_runtime",
            language="javascript",
            file_path="app.js",
            line_in_file=10,
            severity="error",
        )
        assert err.line_number == 42
        assert err.language == "javascript"
        assert err.file_path == "app.js"
        assert len(err.context_before) == 2

    def test_full_context_property(self):
        err = IsolatedError(
            line_number=3,
            content="middle",
            context_before=["before1", "before2"],
            context_after=["after1"],
        )
        assert err.full_context == ["before1", "before2", "middle", "after1"]

    def test_full_context_empty_surrounding(self):
        err = IsolatedError(line_number=1, content="only line")
        assert err.full_context == ["only line"]

    def test_to_dict(self):
        err = IsolatedError(
            line_number=5,
            content="ValueError: bad input",
            error_type="python_error",
            language="python",
            file_path="main.py",
            line_in_file=20,
            severity="error",
        )
        d = err.to_dict()
        assert d["line_number"] == 5
        assert d["content"] == "ValueError: bad input"
        assert d["error_type"] == "python_error"
        assert d["language"] == "python"
        assert d["file_path"] == "main.py"
        assert d["line_in_file"] == 20
        assert d["severity"] == "error"


class TestErrorExtractor:
    """Tests for the ErrorExtractor class."""

    def setup_method(self):
        self.extractor = ErrorExtractor()

    def test_extract_python_traceback(self):
        text = """Some normal output
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    result = do_something()
ValueError: invalid input
More output"""
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        traceback_err = [e for e in errors if e.error_type == "python_traceback"]
        assert len(traceback_err) >= 1

    def test_extract_python_error(self):
        text = "ValueError: invalid literal for int()"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "python_error" for e in errors)

    def test_extract_import_error(self):
        text = "ImportError: cannot import name 'foo' from 'bar'"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any("python" in e.error_type for e in errors)

    def test_extract_module_not_found(self):
        text = "ModuleNotFoundError: No module named 'nonexistent'"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1

    def test_extract_rust_error(self):
        text = 'error[E0433]: failed to resolve: use of undeclared crate `serde`'
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "rust_compile" for e in errors)

    def test_extract_rust_borrow_error(self):
        text = 'error: borrow of moved value: `x`'
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "rust_compile" for e in errors)

    def test_extract_go_error(self):
        text = './main.go:10:3: undefined: Foo'
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "go_compile" for e in errors)

    def test_extract_typescript_error(self):
        text = "error TS2304: Cannot find name 'foo'"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "typescript_compile" for e in errors)

    def test_extract_javascript_type_error(self):
        text = "TypeError: Cannot read properties of undefined (reading 'map')"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "js_runtime" for e in errors)

    def test_extract_cpp_error(self):
        text = "src/main.cpp:42:5: error: use of undeclared identifier 'foo'"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "cpp_compile" for e in errors)

    def test_extract_segfault(self):
        text = "Segmentation fault (core dumped)"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "segfault" for e in errors)

    def test_extract_oom(self):
        text = "Out of memory: Kill process 1234"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "oom" for e in errors)

    def test_extract_panic(self):
        text = "panic: runtime error: index out of range"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "panic" for e in errors)

    def test_extract_github_actions_error(self):
        text = "##[error]Process completed with exit code 1"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "github_actions" for e in errors)

    def test_extract_npm_error(self):
        text = "npm ERR! code ELIFECYCLE"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "npm_error" for e in errors)

    def test_extract_test_failure(self):
        text = "FAILED test_foo.py::test_bar - AssertionError: expected 42"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any(e.error_type == "test_failure" for e in errors)

    def test_extract_generic_error(self):
        text = "[ERROR] Connection refused"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        assert any("error" in e.error_type for e in errors)

    def test_no_errors_in_clean_output(self):
        text = """Building project...
Compiling module A... done
Compiling module B... done
All tests passed!"""
        errors = self.extractor.extract_from_text(text)
        # "Compiling" and "done" should not match error patterns
        # Note: "All tests passed" shouldn't match either
        assert len(errors) == 0 or all(
            e.error_type not in ["python_error", "python_traceback", "rust_compile"]
            for e in errors
        )

    def test_context_before_and_after(self):
        text = """line 1
line 2
line 3
ValueError: bad value
line 5
line 6
line 7"""
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        err = errors[0]
        # Should have context lines
        assert len(err.context_before) > 0 or len(err.context_after) > 0

    def test_custom_context_size(self):
        extractor = ErrorExtractor(context_size=2)
        text = """a
b
c
ValueError: bad
d
e
f"""
        errors = extractor.extract_from_text(text)
        assert len(errors) >= 1
        err = errors[0]
        assert len(err.context_before) <= 2
        assert len(err.context_after) <= 2

    def test_extract_from_lines(self):
        lines = [
            "some log output",
            "TypeError: foo is not a function",
            "more output",
        ]
        errors = self.extractor.extract_from_lines(lines)
        assert len(errors) >= 1

    def test_file_path_extraction_python(self):
        text = '  File "src/app.py", line 42, in process'
        errors = self.extractor.extract_from_text(text)
        # The extractor should detect the file path
        fp, ln = self.extractor.extract_file_path(text, "python")
        assert fp == "src/app.py"
        assert ln == 42

    def test_file_path_extraction_rust(self):
        text = "src/main.rs:10:5"
        fp, ln = self.extractor.extract_file_path(text, "rust")
        assert fp == "src/main.rs"
        assert ln == 10

    def test_file_path_extraction_go(self):
        text = "./handler.go:25:3"
        fp, ln = self.extractor.extract_file_path(text, "go")
        assert fp == "./handler.go"
        assert ln == 25

    def test_file_path_extraction_typescript(self):
        text = "src/index.ts:15:7"
        fp, ln = self.extractor.extract_file_path(text, "typescript")
        assert fp == "src/index.ts"
        assert ln == 15

    def test_file_path_extraction_cpp(self):
        text = "src/engine.cpp:100:12"
        fp, ln = self.extractor.extract_file_path(text, "cpp")
        assert fp == "src/engine.cpp"
        assert ln == 100

    def test_file_path_no_match(self):
        text = "some random text without file paths"
        fp, ln = self.extractor.extract_file_path(text)
        assert fp is None
        assert ln is None

    def test_detect_language_python(self):
        lang = self.extractor.detect_language("ValueError: invalid input")
        assert lang == "python"

    def test_detect_language_rust(self):
        lang = self.extractor.detect_language('error[E0433]: failed to resolve')
        assert lang == "rust"

    def test_detect_language_javascript(self):
        lang = self.extractor.detect_language("TypeError: Cannot read properties")
        assert lang == "javascript"

    def test_detect_language_unknown(self):
        lang = self.extractor.detect_language("some random text")
        assert lang is None

    def test_deduplicate_nearby_errors(self):
        text = """ValueError: bad
ValueError: bad
ValueError: also bad"""
        errors = self.extractor.extract_from_text(text)
        deduped = self.extractor.deduplicate(errors)
        # Deduplication should reduce count
        assert len(deduped) <= len(errors)

    def test_deduplicate_empty_list(self):
        assert self.extractor.deduplicate([]) == []

    def test_deduplicate_single_error(self):
        errors = [IsolatedError(line_number=1, content="Error: test")]
        deduped = self.extractor.deduplicate(errors)
        assert len(deduped) == 1

    def test_multiple_errors_in_one_log(self):
        text = """Build started...
error[E0433]: failed to resolve: use of undeclared crate
ValueError: invalid literal
TypeError: Cannot read properties of undefined"""
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 2

    def test_stream_extract_basic(self):
        lines = [
            "normal line",
            "ValueError: bad value",
            "another line",
        ]
        results = list(self.extractor.stream_extract(iter(lines)))
        assert len(results) >= 1

    def test_line_number_correctness(self):
        text = """line 1
line 2
line 3
ValueError: bad
line 5"""
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
        # ValueError is on line 4 (1-indexed)
        assert errors[0].line_number == 4

    def test_fatal_error(self):
        text = "FATAL: database connection failed"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1

    def test_exception_pattern(self):
        text = "Exception: something went wrong during processing"
        errors = self.extractor.extract_from_text(text)
        assert len(errors) >= 1
