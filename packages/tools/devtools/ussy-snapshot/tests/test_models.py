"""Tests for snapshot data models."""

import json
from datetime import datetime, timezone

from snapshot.models import (
    CursorPosition,
    OpenFile,
    EditorState,
    TerminalState,
    ProcessRecord,
    EnvironmentState,
    MentalContext,
    SnapshotMetadata,
    Snapshot,
)


class TestCursorPosition:
    def test_defaults(self):
        c = CursorPosition()
        assert c.line == 1
        assert c.column == 1

    def test_custom(self):
        c = CursorPosition(line=42, column=15)
        assert c.line == 42
        assert c.column == 15


class TestOpenFile:
    def test_defaults(self):
        f = OpenFile()
        assert f.path == ""
        assert f.cursor.line == 1
        assert f.is_modified is False
        assert f.unsaved_content is None

    def test_custom(self):
        f = OpenFile(path="/tmp/test.py", cursor=CursorPosition(line=10), is_modified=True, unsaved_content="x=1")
        assert f.path == "/tmp/test.py"
        assert f.cursor.line == 10
        assert f.is_modified is True
        assert f.unsaved_content == "x=1"


class TestEditorState:
    def test_defaults(self):
        e = EditorState()
        assert e.editor_type == ""
        assert e.open_files == []
        assert e.breakpoints == []
        assert e.layout is None

    def test_with_files(self):
        files = [OpenFile(path="a.py"), OpenFile(path="b.py")]
        e = EditorState(editor_type="vscode", open_files=files)
        assert e.editor_type == "vscode"
        assert len(e.open_files) == 2


class TestTerminalState:
    def test_defaults(self):
        t = TerminalState()
        assert t.session_id == ""
        assert t.working_directory == ""
        assert t.environment == {}
        assert t.command_history == []
        assert t.running_processes == []
        assert t.screen_buffer == ""
        assert t.foreground_command == ""

    def test_custom(self):
        t = TerminalState(
            session_id="tmux:main:0",
            working_directory="/home/user/project",
            environment={"PATH": "/usr/bin"},
            command_history=["ls", "cd"],
            foreground_command="vim",
        )
        assert t.session_id == "tmux:main:0"
        assert t.working_directory == "/home/user/project"
        assert len(t.command_history) == 2


class TestProcessRecord:
    def test_defaults(self):
        p = ProcessRecord()
        assert p.pid == 0
        assert p.command == ""
        assert p.arguments == []
        assert p.auto_restart is False

    def test_custom(self):
        p = ProcessRecord(
            pid=1234,
            command="python",
            arguments=["-m", "http.server"],
            startup_command="python -m http.server",
            auto_restart=True,
        )
        assert p.pid == 1234
        assert p.startup_command == "python -m http.server"
        assert p.auto_restart is True


class TestEnvironmentState:
    def test_defaults(self):
        e = EnvironmentState()
        assert e.variables == {}
        assert e.path_entries == []
        assert e.python_path_entries == []
        assert e.env_files == []

    def test_custom(self):
        e = EnvironmentState(
            variables={"HOME": "/home/user"},
            path_entries=["/usr/bin"],
            env_files=[".env"],
        )
        assert e.variables["HOME"] == "/home/user"
        assert len(e.path_entries) == 1


class TestMentalContext:
    def test_defaults(self):
        m = MentalContext()
        assert m.note == ""
        assert m.auto_suggestion == ""
        assert m.git_branch == ""
        assert m.git_status_summary == ""
        assert m.timestamp != ""  # auto-computed

    def test_auto_timestamp(self):
        m = MentalContext()
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(m.timestamp)
        assert dt.tzinfo is not None

    def test_custom(self):
        m = MentalContext(note="Was about to wire up callback", git_branch="feature-auth")
        assert m.note == "Was about to wire up callback"
        assert m.git_branch == "feature-auth"


class TestSnapshotMetadata:
    def test_defaults(self):
        m = SnapshotMetadata()
        assert m.name == ""
        assert m.created_at != ""  # auto-computed
        assert m.tags == []
        assert m.terminal_count == 0
        assert m.file_count == 0
        assert m.process_count == 0

    def test_auto_timestamp(self):
        m = SnapshotMetadata(name="test")
        dt = datetime.fromisoformat(m.created_at)
        assert dt.tzinfo is not None


class TestSnapshot:
    def test_defaults(self):
        s = Snapshot()
        assert s.name == ""
        assert s.terminals == []
        assert s.editor is not None
        assert s.processes == []

    def test_post_init_metadata_counts(self):
        s = Snapshot(
            name="test",
            terminals=[TerminalState(session_id="t1")],
            processes=[ProcessRecord(pid=1)],
            editor=EditorState(open_files=[OpenFile(path="a.py")]),
        )
        assert s.metadata.terminal_count == 1
        assert s.metadata.file_count == 1
        assert s.metadata.process_count == 1
        assert s.metadata.name == "test"

    def test_to_dict(self):
        s = Snapshot(name="test-snap")
        d = s.to_dict()
        assert d["name"] == "test-snap"
        assert "metadata" in d
        assert "terminals" in d

    def test_to_json(self):
        s = Snapshot(name="test-snap")
        j = s.to_json()
        data = json.loads(j)
        assert data["name"] == "test-snap"

    def test_from_dict_roundtrip(self):
        original = Snapshot(
            name="roundtrip-test",
            terminals=[TerminalState(session_id="t1", working_directory="/tmp")],
            editor=EditorState(editor_type="vscode", open_files=[OpenFile(path="main.py", cursor=CursorPosition(line=42))]),
            processes=[ProcessRecord(pid=999, command="python", startup_command="python app.py")],
            environment=EnvironmentState(variables={"HOME": "/tmp"}),
            mental_context=MentalContext(note="test note"),
        )
        d = original.to_dict()
        restored = Snapshot.from_dict(d)
        assert restored.name == "roundtrip-test"
        assert len(restored.terminals) == 1
        assert restored.terminals[0].working_directory == "/tmp"
        assert restored.editor.editor_type == "vscode"
        assert len(restored.editor.open_files) == 1
        assert restored.editor.open_files[0].cursor.line == 42
        assert len(restored.processes) == 1
        assert restored.processes[0].startup_command == "python app.py"
        assert restored.environment.variables["HOME"] == "/tmp"
        assert restored.mental_context.note == "test note"

    def test_from_json_roundtrip(self):
        original = Snapshot(name="json-test", mental_context=MentalContext(note="json note"))
        j = original.to_json()
        restored = Snapshot.from_json(j)
        assert restored.name == "json-test"
        assert restored.mental_context.note == "json note"

    def test_from_dict_handles_nested_cursor(self):
        data = {
            "name": "cursor-test",
            "editor": {
                "open_files": [
                    {"path": "test.py", "cursor": {"line": 5, "column": 10}, "is_modified": False}
                ]
            }
        }
        s = Snapshot.from_dict(data)
        assert s.editor.open_files[0].cursor.line == 5
        assert s.editor.open_files[0].cursor.column == 10
