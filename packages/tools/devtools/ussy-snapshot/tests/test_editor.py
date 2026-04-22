"""Tests for IDE/editor state capture and restore."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from snapshot.editor import (
    detect_active_editor,
    capture_editor_state,
    _parse_vim_session,
    _parse_jetbrains_workspace,
    restore_editor_state,
)
from snapshot.models import EditorState, OpenFile, CursorPosition


class TestDetectActiveEditor:
    def test_returns_string(self):
        editor = detect_active_editor()
        assert isinstance(editor, str)
        assert editor in ("vscode", "jetbrains", "neovim", "vim", "other")


class TestCaptureEditorState:
    def test_returns_editor_state(self):
        state = capture_editor_state()
        assert isinstance(state, EditorState)

    def test_has_editor_type(self):
        state = capture_editor_state()
        assert state.editor_type != ""


class TestParseVimSession:
    def test_parse_badd(self, tmp_path):
        session = tmp_path / "Session.vim"
        session.write_text(
            "badd +1 src/main.py\n"
            "badd +1 src/utils.py\n"
            "badd +1 tests/test_main.py\n"
        )
        files = _parse_vim_session(session)
        assert len(files) == 3
        assert files[0].path == "src/main.py"
        assert files[1].path == "src/utils.py"
        assert files[2].path == "tests/test_main.py"

    def test_parse_edit(self, tmp_path):
        session = tmp_path / "Session.vim"
        session.write_text("edit /home/user/project/app.py\n")
        files = _parse_vim_session(session)
        assert len(files) == 1
        assert files[0].path == "/home/user/project/app.py"

    def test_parse_nonexistent(self, tmp_path):
        session = tmp_path / "nonexistent.vim"
        files = _parse_vim_session(session)
        assert files == []


class TestParseJetbrainsWorkspace:
    def test_parse_file_uris(self, tmp_path):
        workspace = tmp_path / "workspace.xml"
        workspace.write_text(
            '<project>\n'
            '  <file url="file:///home/user/src/Main.java" />\n'
            '  <file url="file:///home/user/src/Utils.java" />\n'
            '</project>\n'
        )
        files = _parse_jetbrains_workspace(workspace)
        assert len(files) >= 2
        paths = [f.path for f in files]
        assert "/home/user/src/Main.java" in paths
        assert "/home/user/src/Utils.java" in paths

    def test_parse_nonexistent(self, tmp_path):
        workspace = tmp_path / "nope.xml"
        files = _parse_jetbrains_workspace(workspace)
        assert files == []


class TestRestoreEditorState:
    def test_restore_empty_files(self):
        state = EditorState(editor_type="other", open_files=[])
        result = restore_editor_state(state, dry_run=True)
        assert result is True

    def test_restore_dry_run(self):
        state = EditorState(
            editor_type="vim",
            open_files=[OpenFile(path="/tmp/test.py")],
        )
        result = restore_editor_state(state, dry_run=True)
        assert result is True

    def test_restore_with_existing_files(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        state = EditorState(
            editor_type="other",
            open_files=[OpenFile(path=str(test_file))],
        )
        # In dry_run mode this should succeed
        result = restore_editor_state(state, dry_run=True)
        assert result is True
