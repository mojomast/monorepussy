"""Tests for CLI interface."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from ussy_snapshot.cli import main, create_parser


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    old_env = os.environ.get("SNAPSHOT_DIR")
    os.environ["SNAPSHOT_DIR"] = str(snap_dir)
    yield snap_dir
    if old_env is not None:
        os.environ["SNAPSHOT_DIR"] = old_env
    else:
        os.environ.pop("SNAPSHOT_DIR", None)


class TestParser:
    def test_no_command(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert getattr(args, "command", None) is None

    def test_save_command(self):
        parser = create_parser()
        args = parser.parse_args(["save", "test-snap"])
        assert args.command == "save"
        assert args.name == "test-snap"

    def test_save_with_note(self):
        parser = create_parser()
        args = parser.parse_args(["save", "test-snap", "--note", "my note"])
        assert args.note == "my note"

    def test_load_command(self):
        parser = create_parser()
        args = parser.parse_args(["load", "test-snap"])
        assert args.command == "load"
        assert args.name == "test-snap"

    def test_new_command(self):
        parser = create_parser()
        args = parser.parse_args(["new", "fresh-snap"])
        assert args.command == "new"
        assert args.name == "fresh-snap"

    def test_list_command(self):
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"
        assert args.sort == "age"

    def test_list_sort_name(self):
        parser = create_parser()
        args = parser.parse_args(["list", "--sort", "name"])
        assert args.sort == "name"

    def test_peek_command(self):
        parser = create_parser()
        args = parser.parse_args(["peek", "test-snap"])
        assert args.command == "peek"

    def test_prune_command(self):
        parser = create_parser()
        args = parser.parse_args(["prune", "--older-than", "7d"])
        assert args.command == "prune"
        assert args.older_than == "7d"

    def test_diff_command(self):
        parser = create_parser()
        args = parser.parse_args(["diff", "snap1", "snap2"])
        assert args.command == "diff"
        assert args.name1 == "snap1"
        assert args.name2 == "snap2"

    def test_export_command(self):
        parser = create_parser()
        args = parser.parse_args(["export", "snap1"])
        assert args.command == "export"

    def test_import_command(self):
        parser = create_parser()
        args = parser.parse_args(["import", "snap.tar.gz"])
        assert args.command == "import"
        assert args.path == "snap.tar.gz"

    def test_tag_command(self):
        parser = create_parser()
        args = parser.parse_args(["tag", "snap1", "v1"])
        assert args.command == "tag"
        assert args.tag == "v1"

    def test_untag_command(self):
        parser = create_parser()
        args = parser.parse_args(["untag", "snap1", "v1"])
        assert args.command == "untag"


class TestMainFunction:
    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0

    def test_version(self):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0

    def test_save_command(self, storage_dir):
        result = main(["save", "cli-test", "--note", "CLI test"])
        assert result == 0

    def test_load_nonexistent(self, storage_dir):
        result = main(["load", "nonexistent-snap", "--dry-run"])
        assert result == 1

    def test_list_empty(self, storage_dir):
        result = main(["list"])
        assert result == 0

    def test_peek_nonexistent(self, storage_dir):
        result = main(["peek", "nonexistent"])
        assert result == 1

    def test_new_command(self, storage_dir):
        result = main(["new", "cli-new-test"])
        assert result == 0

    def test_tag_command(self, storage_dir):
        main(["save", "tag-cli-test"])
        result = main(["tag", "tag-cli-test", "milestone"])
        assert result == 0

    def test_tag_nonexistent(self, storage_dir):
        result = main(["tag", "nonexistent", "tag"])
        assert result == 1

    def test_untag_command(self, storage_dir):
        main(["save", "untag-cli-test"])
        main(["tag", "untag-cli-test", "remove-me"])
        result = main(["untag", "untag-cli-test", "remove-me"])
        assert result == 0

    def test_diff_command(self, storage_dir):
        main(["save", "diff1"])
        main(["save", "diff2"])
        result = main(["diff", "diff1", "diff2"])
        assert result == 0

    def test_diff_nonexistent(self, storage_dir):
        result = main(["diff", "no1", "no2"])
        assert result == 1

    def test_prune_command(self, storage_dir):
        result = main(["prune", "--dry-run"])
        assert result == 0

    def test_export_import_roundtrip(self, storage_dir, tmp_path):
        main(["save", "export-cli-test", "--note", "CLI export test"])
        output = str(tmp_path / "export.tar.gz")
        result = main(["export", "export-cli-test", "--output", output])
        assert result == 0
        assert os.path.exists(output)

    def test_load_existing(self, storage_dir):
        main(["save", "load-cli-test", "--note", "load test"])
        result = main(["load", "load-cli-test", "--dry-run"])
        assert result == 0

    def test_peek_existing(self, storage_dir):
        main(["save", "peek-cli-test", "--note", "peek test"])
        result = main(["peek", "peek-cli-test"])
        assert result == 0
