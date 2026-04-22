"""Data models for Snapshot — all dataclasses for development state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class CursorPosition:
    """Cursor position in a file (1-indexed)."""
    line: int = 1
    column: int = 1


@dataclass
class OpenFile:
    """An open file in an editor."""
    path: str = ""
    cursor: CursorPosition = field(default_factory=CursorPosition)
    is_modified: bool = False
    unsaved_content: Optional[str] = None


@dataclass
class EditorState:
    """State of an IDE/editor session."""
    editor_type: str = ""  # "vscode", "jetbrains", "neovim", "vim", "other"
    open_files: List[OpenFile] = field(default_factory=list)
    breakpoints: List[Dict[str, Any]] = field(default_factory=list)
    layout: Optional[Dict[str, Any]] = None


@dataclass
class TerminalState:
    """State of a single terminal session."""
    session_id: str = ""
    working_directory: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    command_history: List[str] = field(default_factory=list)
    running_processes: List[Dict[str, Any]] = field(default_factory=list)
    screen_buffer: str = ""
    foreground_command: str = ""


@dataclass
class ProcessRecord:
    """A record of a running process that can be restarted."""
    pid: int = 0
    command: str = ""
    arguments: List[str] = field(default_factory=list)
    working_directory: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    startup_command: str = ""  # Full command string for restart
    auto_restart: bool = False


@dataclass
class EnvironmentState:
    """Project-relevant environment variables."""
    variables: Dict[str, str] = field(default_factory=dict)
    path_entries: List[str] = field(default_factory=list)
    python_path_entries: List[str] = field(default_factory=list)
    env_files: List[str] = field(default_factory=list)  # .env files found


@dataclass
class MentalContext:
    """Mental context — the 'about to type' state."""
    note: str = ""
    auto_suggestion: str = ""
    git_branch: str = ""
    git_status_summary: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SnapshotMetadata:
    """Metadata about a snapshot."""
    name: str = ""
    created_at: str = ""
    tags: List[str] = field(default_factory=list)
    terminal_count: int = 0
    file_count: int = 0
    process_count: int = 0
    note_preview: str = ""
    size_bytes: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Snapshot:
    """Complete development state snapshot."""
    name: str = ""
    metadata: SnapshotMetadata = field(default_factory=SnapshotMetadata)
    terminals: List[TerminalState] = field(default_factory=list)
    editor: EditorState = field(default_factory=EditorState)
    processes: List[ProcessRecord] = field(default_factory=list)
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    mental_context: MentalContext = field(default_factory=MentalContext)

    def __post_init__(self):
        if self.metadata and not self.metadata.name:
            self.metadata.name = self.name
        if self.metadata:
            self.metadata.terminal_count = len(self.terminals)
            self.metadata.file_count = len(self.editor.open_files) if self.editor else 0
            self.metadata.process_count = len(self.processes)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to a dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize snapshot to JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Deserialize snapshot from a dictionary."""
        # Reconstruct nested dataclasses
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = SnapshotMetadata(**data["metadata"])
        if "editor" in data and isinstance(data["editor"], dict):
            editor_data = data["editor"]
            if "open_files" in editor_data and isinstance(editor_data["open_files"], list):
                editor_data["open_files"] = [
                    OpenFile(**{**f, "cursor": CursorPosition(**f["cursor"])})
                    if isinstance(f, dict) and "cursor" in f and isinstance(f["cursor"], dict)
                    else OpenFile(**f) if isinstance(f, dict) else f
                    for f in editor_data["open_files"]
                ]
            data["editor"] = EditorState(**editor_data)
        if "terminals" in data and isinstance(data["terminals"], list):
            data["terminals"] = [
                TerminalState(**t) if isinstance(t, dict) else t
                for t in data["terminals"]
            ]
        if "processes" in data and isinstance(data["processes"], list):
            data["processes"] = [
                ProcessRecord(**p) if isinstance(p, dict) else p
                for p in data["processes"]
            ]
        if "environment" in data and isinstance(data["environment"], dict):
            data["environment"] = EnvironmentState(**data["environment"])
        if "mental_context" in data and isinstance(data["mental_context"], dict):
            data["mental_context"] = MentalContext(**data["mental_context"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "Snapshot":
        """Deserialize snapshot from JSON."""
        return cls.from_dict(json.loads(json_str))
