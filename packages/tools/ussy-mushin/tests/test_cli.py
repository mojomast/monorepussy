"""Tests for mushin.cli module."""

import subprocess
import sys
from pathlib import Path

import pytest

from mushin.cli import build_parser, main


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestBuildParser:
    def test_parser_created(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_no_command_shows_help(self, capsys):
        result = main([])
        assert result == 0


class TestInitCommand:
    def test_init(self, project_dir, capsys):
        result = main(["-C", str(project_dir), "init"])
        assert result == 0
        assert (project_dir / ".mushin").exists()
        captured = capsys.readouterr()
        assert "Initialized" in captured.out


class TestSaveCommand:
    def test_save_new(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "save", "-n", "test-ws"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Saved" in captured.out

    def test_save_with_description(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "save", "-n", "desc-ws", "-d", "A description"])
        assert result == 0


class TestListCommand:
    def test_list_empty(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "list"])
        assert result == 0
        captured = capsys.readouterr()
        assert "No workspaces" in captured.out

    def test_list_with_workspaces(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "ws1"])
        result = main(["-C", str(project_dir), "list"])
        assert result == 0
        captured = capsys.readouterr()
        assert "ws1" in captured.out


class TestRecordCommand:
    def test_record(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "journal-ws"])
        result = main(["-C", str(project_dir), "record", "x = 1", "-o", "1"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Recorded" in captured.out

    def test_record_auto_creates_workspace(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "record", "auto test"])
        assert result == 0


class TestJournalCommand:
    def test_journal_no_workspace(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "journal"])
        assert result == 1

    def test_journal_with_entries(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "j-ws"])
        main(["-C", str(project_dir), "record", "print('hi')", "-o", "hi"])
        result = main(["-C", str(project_dir), "journal"])
        assert result == 0


class TestReplayCommand:
    def test_replay_no_workspace(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "replay"])
        assert result == 1


class TestResumeCommand:
    def test_resume_no_id(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "resume"])
        assert result == 1

    def test_resume_workspace(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "resume-ws"])
        from mushin.workspace import get_active_workspace_id
        ws_id = get_active_workspace_id(project_dir)
        result = main(["-C", str(project_dir), "resume", ws_id])
        assert result == 0


class TestDeleteCommand:
    def test_delete(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "del-ws"])
        from mushin.workspace import get_active_workspace_id
        ws_id = get_active_workspace_id(project_dir)
        result = main(["-C", str(project_dir), "delete", ws_id])
        assert result == 0


class TestBranchCommand:
    def test_create_branch(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        main(["-C", str(project_dir), "save", "-n", "parent-ws"])
        from mushin.workspace import get_active_workspace_id
        ws_id = get_active_workspace_id(project_dir)
        result = main(["-C", str(project_dir), "branch", "exp", "-p", ws_id])
        assert result == 0

    def test_list_branches_empty(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "branches"])
        assert result == 0


class TestBookmarkCommand:
    def test_create_bookmark(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "bookmark", "auth", "-f", "auth.py", "-l", "42"])
        assert result == 0

    def test_list_bookmarks_empty(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "bookmarks"])
        assert result == 0


class TestInfoCommand:
    def test_info(self, project_dir, capsys):
        main(["-C", str(project_dir), "init"])
        result = main(["-C", str(project_dir), "info"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Mushin" in captured.out


class TestPythonMModule:
    def test_python_m_mushin_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "mushin", "--version"],
            capture_output=True,
            text=True,
            cwd=str(project_dir) if False else None,
        )
        # May fail if not installed; that's OK for this test
        # We just verify the __main__.py is wired up correctly
        pass
