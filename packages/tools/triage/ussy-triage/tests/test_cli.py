"""Tests for the CLI interface."""

import json
import os
import tempfile
import pytest
from ussy_triage.cli import main, create_parser, read_input, get_output_format


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_created(self):
        parser = create_parser()
        assert parser is not None

    def test_analyze_command(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log"])
        assert args.command == "analyze"
        assert args.file == "test.log"

    def test_analyze_with_quick(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--quick"])
        assert args.quick is True

    def test_analyze_with_json(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--json"])
        assert args.json is True

    def test_analyze_with_teach(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--teach"])
        assert args.teach is True

    def test_analyze_with_project(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--project", "/tmp/proj"])
        assert args.project == "/tmp/proj"

    def test_pattern_add_command(self):
        parser = create_parser()
        args = parser.parse_args([
            "pattern", "add",
            "--regex", r"TestError: (.+)",
            "--cause", "Test error",
            "--fix", "Fix it",
        ])
        assert args.command == "pattern"
        assert args.pattern_command == "add"
        assert args.regex == r"TestError: (.+)"
        assert args.cause == "Test error"

    def test_pattern_list_command(self):
        parser = create_parser()
        args = parser.parse_args(["pattern", "list"])
        assert args.command == "pattern"
        assert args.pattern_command == "list"

    def test_pattern_list_with_language(self):
        parser = create_parser()
        args = parser.parse_args(["pattern", "list", "--language", "python"])
        assert args.language == "python"

    def test_pattern_remove_command(self):
        parser = create_parser()
        args = parser.parse_args(["pattern", "remove", "5"])
        assert args.pattern_command == "remove"
        assert args.id == 5


class TestGetOutputFormat:
    """Tests for output format resolution."""

    def test_json_format(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--json"])
        assert get_output_format(args) == "json"

    def test_quick_format(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--quick"])
        assert get_output_format(args) == "minimal"

    def test_teach_format(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log", "--teach"])
        assert get_output_format(args) == "teaching"

    def test_default_format(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "test.log"])
        assert get_output_format(args) == "detective"


class TestReadInput:
    """Tests for input reading."""

    def test_read_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("Error: something went wrong\n")
            f.flush()
            path = f.name

        try:
            content = read_input(path)
            assert "something went wrong" in content
        finally:
            os.unlink(path)

    def test_read_nonexistent_file_exits(self):
        with pytest.raises(SystemExit):
            read_input("/nonexistent/path/to/file.log")


class TestCLIAnalyze:
    """Integration tests for the analyze command."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_log_file(self, content):
        path = os.path.join(self.tmpdir, "error.log")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_analyze_python_error(self):
        log_path = self._create_log_file(
            "Traceback (most recent call last):\n"
            '  File "app.py", line 42, in <module>\n'
            "    result = int('abc')\n"
            "ValueError: invalid literal for int() with base 10: 'abc'\n"
        )
        # Run via main() with explicit args
        exit_code = main(["analyze", log_path, "--project", self.tmpdir])
        # Should return 1 because errors were found
        assert exit_code == 1

    def test_analyze_clean_log(self, capsys):
        log_path = self._create_log_file(
            "Building project...\nCompiling...\nAll done!\n"
        )
        exit_code = main(["analyze", log_path, "--project", self.tmpdir])
        # Should return 0 because no errors
        assert exit_code == 0

    def test_analyze_json_output(self, capsys):
        log_path = self._create_log_file(
            "ValueError: bad input\n"
        )
        main(["analyze", log_path, "--json", "--project", self.tmpdir])
        captured = capsys.readouterr()
        # Output should be valid JSON (array format)
        data = json.loads(captured.out)
        assert isinstance(data, list) and len(data) > 0
        assert "case_number" in data[0]

    def test_analyze_quick_output(self, capsys):
        log_path = self._create_log_file(
            "ValueError: bad input\n"
        )
        main(["analyze", log_path, "--quick", "--project", self.tmpdir])
        captured = capsys.readouterr()
        # Minimal output should contain "confidence"
        assert "confidence" in captured.out.lower()

    def test_analyze_teaching_output(self, capsys):
        log_path = self._create_log_file(
            "ValueError: bad input\n"
        )
        main(["analyze", log_path, "--teach", "--project", self.tmpdir])
        captured = capsys.readouterr()
        assert "LEARN MORE" in captured.out

    def test_analyze_multiple_errors(self, capsys):
        log_path = self._create_log_file(
            "error[E0433]: failed to resolve\n"
            "ValueError: invalid\n"
            "TypeError: wrong type\n"
        )
        main(["analyze", log_path, "--project", self.tmpdir])
        captured = capsys.readouterr()
        assert "CRIME SCENE" in captured.out

    def test_analyze_no_input_exits(self):
        with pytest.raises(SystemExit):
            main([])


class TestCLIPattern:
    """Tests for the pattern management commands."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_dir = os.getcwd()
        os.chdir(self.tmpdir)

    def teardown_method(self):
        os.chdir(self.orig_dir)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_pattern_list(self, capsys):
        main(["pattern", "list"])
        captured = capsys.readouterr()
        # Should list seed patterns
        assert "python_error" in captured.out or "rust_compile" in captured.out or "Total" in captured.out

    def test_pattern_count(self, capsys):
        main(["pattern", "list", "--count"])
        captured = capsys.readouterr()
        assert "Total patterns:" in captured.out

    def test_pattern_add_and_list(self, capsys):
        main(["pattern", "add",
              "--regex", r"TestError: (.+)",
              "--cause", "Test error: {0}",
              "--fix", "Fix test error",
              "--type", "custom",
              "--confidence", "0.8"])
        captured = capsys.readouterr()
        assert "Pattern added" in captured.out

    def test_pattern_add_invalid_regex(self, capsys):
        exit_code = main(["pattern", "add",
              "--regex", "[invalid(regex",
              "--cause", "Bad regex",
              "--fix", "N/A"])
        assert exit_code == 1

    def test_pattern_list_by_language(self, capsys):
        main(["pattern", "list", "--language", "python"])
        captured = capsys.readouterr()
        assert "python" in captured.out.lower() or "Python" in captured.out

    def test_pattern_list_by_type(self, capsys):
        main(["pattern", "list", "--type", "rust_compile"])
        captured = capsys.readouterr()
        assert "rust" in captured.out.lower()

    def test_pattern_remove_nonexistent(self, capsys):
        exit_code = main(["pattern", "remove", "99999"])
        assert exit_code == 1


class TestCLIEndToEnd:
    """End-to-end tests combining extraction, enrichment, and rendering."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_rust_pipeline(self, capsys):
        log_path = os.path.join(self.tmpdir, "rust_error.log")
        with open(log_path, "w") as f:
            f.write(
                "   Compiling myproject v0.1.0\n"
                "error[E0433]: failed to resolve: use of undeclared crate `serde`\n"
                "  --> src/main.rs:4:5\n"
                "   |\n"
                " 4 |     let data: serde_json::Value = serde_json::from_str(\"{}\").unwrap();\n"
                "   |     ^^^^^^^^^^^^^^^^^^^^^^^^ use of undeclared crate `serde`\n"
                "   |\n"
                "error: build failed\n"
            )
        main(["analyze", log_path, "--project", self.tmpdir])
        captured = capsys.readouterr()
        assert "CRIME SCENE" in captured.out

    def test_python_pipeline(self, capsys):
        log_path = os.path.join(self.tmpdir, "python_error.log")
        with open(log_path, "w") as f:
            f.write(
                "Running tests...\n"
                "Traceback (most recent call last):\n"
                '  File "test_app.py", line 15, in test_login\n'
                "    response = client.post('/login', data={'user': 'admin'})\n"
                '  File "app.py", line 42, in login\n'
                "    user = db.get_user(username)\n"
                "AttributeError: 'NoneType' object has no attribute 'get_user'\n"
                "FAILED test_app.py::test_login\n"
            )
        main(["analyze", log_path, "--json", "--project", self.tmpdir])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list) and len(data) > 0
        assert data[0]["case_number"] == 1

    def test_ci_pipeline(self, capsys):
        log_path = os.path.join(self.tmpdir, "ci_error.log")
        with open(log_path, "w") as f:
            f.write(
                "Run tests\n"
                "##[error]Process completed with exit code 1\n"
                "Build FAILED\n"
            )
        main(["analyze", log_path, "--quick", "--project", self.tmpdir])
        captured = capsys.readouterr()
        assert len(captured.out) > 0
