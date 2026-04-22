"""Tests for the CLI interface."""

import os
import sys
from unittest.mock import patch

import pytest

from ussy_kintsugi.cli import main, build_parser


class TestBuildParser:
    """Test argument parser construction."""

    def test_parser_has_mark(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["mark"])
        # mark requires --bug, --break-desc, --repair, location
        assert exc_info.value.code == 2

    def test_parser_mark_command(self):
        parser = build_parser()
        args = parser.parse_args(
            ["mark", "--bug", "X-1", "--break-desc", "broke", "--repair", "fixed", "test.py:42"]
        )
        assert args.command == "mark"
        assert args.bug == "X-1"
        assert args.location == "test.py:42"

    def test_parser_map_command(self):
        parser = build_parser()
        args = parser.parse_args(["map", "src/"])
        assert args.command == "map"
        assert args.path == "src/"

    def test_parser_stress_command(self):
        parser = build_parser()
        args = parser.parse_args(["stress"])
        assert args.command == "stress"
        assert args.no_ast is False

    def test_parser_stress_no_ast_flag(self):
        parser = build_parser()
        args = parser.parse_args(["stress", "--no-ast"])
        assert args.command == "stress"
        assert args.no_ast is True

    def test_parser_archaeology_command(self):
        parser = build_parser()
        args = parser.parse_args(["archaeology", "test.py"])
        assert args.command == "archaeology"
        assert args.file == "test.py"

    def test_parser_hollow_command(self):
        parser = build_parser()
        args = parser.parse_args(["hollow"])
        assert args.command == "hollow"

    def test_parser_list_command(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_version(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestMainNoCommand:
    """Test main with no subcommand."""

    def test_no_command_prints_help(self, capsys):
        main([])
        captured = capsys.readouterr()
        assert "kintsugi" in captured.out.lower() or "usage" in captured.out.lower()


class TestMarkCommand:
    """Test the mark command."""

    def test_mark_creates_joint(self, tmp_path, capsys):
        # Create a dummy file to annotate
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    pass\n")

        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.save.return_value = None

            main(
                [
                    "mark",
                    "--bug",
                    "PROJ-892",
                    "--severity",
                    "critical",
                    "--break-desc",
                    "user.email was None",
                    "--repair",
                    "Added None guard",
                    "--removal-impact",
                    "TypeError crash",
                    "--test",
                    "test_oauth_null_email",
                    str(f) + ":2",
                ]
            )

        captured = capsys.readouterr()
        assert "Golden joint marked" in captured.out


class TestMapCommand:
    """Test the map command."""

    def test_map_no_joints(self, tmp_path, capsys):
        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.load_all.return_value = []

            with patch("ussy_kintsugi.cli.scan_directory", return_value=[]):
                main(["map", "--root", str(tmp_path)])

        captured = capsys.readouterr()
        assert "No golden joints found" in captured.out


class TestHollowCommand:
    """Test the hollow command."""

    def test_hollow_none_found(self, tmp_path, capsys):
        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.load_all.return_value = []
            mock_store.find_hollow.return_value = []

            main(["hollow", "--root", str(tmp_path)])

        captured = capsys.readouterr()
        assert "No hollow joints" in captured.out

    def test_hollow_found(self, tmp_path, capsys):
        from ussy_kintsugi.joint import Joint

        j = Joint(
            id="j-test",
            file="test.py",
            line=1,
            bug_ref="X-1",
            status="hollow",
            break_description="bug",
            repair_description="fix",
            timestamp="2024-01-01T00:00:00+00:00",
        )

        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.find_hollow.return_value = [j]

            main(["hollow", "--root", str(tmp_path)])

        captured = capsys.readouterr()
        assert "j-test" in captured.out


class TestListCommand:
    """Test the list command."""

    def test_list_empty(self, tmp_path, capsys):
        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.load_all.return_value = []

            main(["list", "--root", str(tmp_path)])

        captured = capsys.readouterr()
        assert "No golden joints" in captured.out

    def test_list_with_joints(self, tmp_path, capsys):
        from ussy_kintsugi.joint import Joint

        j = Joint(
            id="j-test",
            file="test.py",
            line=1,
            bug_ref="X-1",
            severity="critical",
            break_description="big bug",
            timestamp="2024-01-01T00:00:00+00:00",
        )

        with patch("ussy_kintsugi.cli.JointStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.load_all.return_value = [j]

            main(["list", "--root", str(tmp_path)])

        captured = capsys.readouterr()
        assert "j-test" in captured.out
