"""Tests for the CLI module."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from fossilrecord.cli import main as cli_main


class TestCLIBasic:
    """Basic CLI tests."""

    def test_no_args_returns_zero(self):
        # No command should print help and return 0
        result = cli_main([])
        assert result == 0

    def test_version(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--version"])
        assert exc_info.value.code == 0

    def test_unknown_command(self):
        # argparse handles unknown commands
        with pytest.raises(SystemExit):
            cli_main(["nonexistent_command"])


class TestCLICorpus:
    """Tests for the corpus subcommand."""

    def test_corpus_list(self, capsys):
        result = cli_main(["corpus"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Corpus" in captured.out

    def test_corpus_list_languages(self, capsys):
        result = cli_main(["corpus", "--list-languages"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Brainfuck" in captured.out

    def test_corpus_list_categories(self, capsys):
        result = cli_main(["corpus", "--list-categories"])
        assert result == 0
        captured = capsys.readouterr()
        assert "minimalistic" in captured.out or "whitespace" in captured.out

    def test_corpus_filter_by_language(self, capsys):
        result = cli_main(["corpus", "--language", "Brainfuck"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Brainfuck" in captured.out

    def test_corpus_filter_by_category(self, capsys):
        result = cli_main(["corpus", "--category", "whitespace"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Whitespace" in captured.out or "whitespace" in captured.out.lower()


class TestCLITest:
    """Tests for the test subcommand."""

    def test_test_runs(self, capsys):
        result = cli_main(["test", "--language", "Brainfuck", "--timeout", "30"])
        assert result == 0
        captured = capsys.readouterr()
        assert "FossilRecord Test Results" in captured.out

    def test_test_with_output(self, tmp_path, capsys):
        output = tmp_path / "results.json"
        result = cli_main(["test", "--language", "Brainfuck", "--timeout", "30", "--output", str(output)])
        assert result == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert "results" in data

    def test_test_with_difficulty_filter(self, capsys):
        result = cli_main(["test", "--min-difficulty", "3", "--max-difficulty", "5", "--timeout", "30"])
        assert result == 0


class TestCLIScore:
    """Tests for the score subcommand."""

    def test_score_runs(self, capsys):
        result = cli_main(["score", "--tool", "test-tool", "--timeout", "30"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Fossil Score" in captured.out

    def test_score_with_output(self, tmp_path, capsys):
        output = tmp_path / "score.json"
        result = cli_main(["score", "--tool", "test-tool", "--timeout", "30", "--output", str(output)])
        assert result == 0
        assert output.exists()


class TestCLIGenerate:
    """Tests for the generate subcommand."""

    def test_generate_runs(self, capsys):
        result = cli_main(["generate", "--count", "5", "--seed", "42"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Generated" in captured.out

    def test_generate_with_output(self, tmp_path, capsys):
        output = tmp_path / "fossils.json"
        result = cli_main(["generate", "--count", "3", "--seed", "42", "--output", str(output)])
        assert result == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["count"] >= 1

    def test_generate_with_category(self, capsys):
        result = cli_main(["generate", "--category", "whitespace", "--count", "3", "--seed", "42"])
        assert result == 0


class TestCLICompare:
    """Tests for the compare subcommand."""

    def test_compare_two_scores(self, tmp_path, capsys):
        # First create two score files
        score_file_a = tmp_path / "score_a.json"
        score_file_b = tmp_path / "score_b.json"

        cli_main(["score", "--tool", "tool-a", "--output", str(score_file_a)])
        cli_main(["score", "--tool", "tool-b", "--output", str(score_file_b)])

        result = cli_main(["compare", str(score_file_a), str(score_file_b)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Comparison" in captured.out


class TestCLILeaderboard:
    """Tests for the leaderboard subcommand."""

    def test_leaderboard_no_files(self, capsys):
        result = cli_main(["leaderboard"])
        assert result == 1  # No files = error

    def test_leaderboard_with_files(self, tmp_path, capsys):
        # Create score files
        for name in ["a", "b", "c"]:
            path = tmp_path / f"score_{name}.json"
            cli_main(["score", "--tool", f"tool-{name}", "--output", str(path)])

        files = [str(tmp_path / f"score_{n}.json") for n in ["a", "b", "c"]]
        result = cli_main(["leaderboard"] + files)
        assert result == 0
        captured = capsys.readouterr()
        assert "Leaderboard" in captured.out
