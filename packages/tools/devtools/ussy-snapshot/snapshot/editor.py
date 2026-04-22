"""IDE/editor state capture and restore."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CursorPosition, EditorState, OpenFile


def detect_active_editor() -> str:
    """Detect which editor(s) are currently running.
    
    Returns the editor type string: "vscode", "jetbrains", "neovim", "vim", or "other".
    """
    # Check for running editor processes
    try:
        result = subprocess.run(
            ["ps", "-eo", "comm="],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            procs = result.stdout.strip().split("\n")
            for proc in procs:
                proc_lower = proc.strip().lower()
                if "code" in proc_lower:
                    return "vscode"
                if "idea" in proc_lower or "pycharm" in proc_lower or "webstorm" in proc_lower:
                    return "jetbrains"
                if "nvim" in proc_lower:
                    return "neovim"
                if proc_lower == "vim":
                    return "vim"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "other"


def capture_editor_state(project_dir: str = "") -> EditorState:
    """Capture the current IDE/editor state.
    
    Args:
        project_dir: Project directory to look for editor session data.
    """
    editor_type = detect_active_editor()
    state = EditorState(editor_type=editor_type)

    if editor_type == "vscode":
        state = _capture_vscode_state(project_dir, state)
    elif editor_type in ("neovim", "vim"):
        state = _capture_vim_state(project_dir, state)
    elif editor_type == "jetbrains":
        state = _capture_jetbrains_state(project_dir, state)

    return state


def _capture_vscode_state(project_dir: str, state: EditorState) -> EditorState:
    """Capture VS Code state from workspace storage."""
    # VS Code stores workspace state in:
    # ~/.config/Code/User/workspaceStorage/<hash>/workspace.json
    # and ~/.config/Code/User/globalStorage/state.vscdb
    
    # Look for open files from VS Code's workspace
    vscode_config = Path.home() / ".config" / "Code"
    if not vscode_config.exists():
        # Try on macOS
        vscode_config = Path.home() / "Library" / "Application Support" / "Code"
    
    if vscode_config.exists():
        # Try to find workspace storage
        ws_storage = vscode_config / "User" / "workspaceStorage"
        if ws_storage.exists():
            state.open_files = _parse_vscode_workspace_files(ws_storage, project_dir)

    return state


def _parse_vscode_workspace_files(ws_storage: Path, project_dir: str) -> List[OpenFile]:
    """Parse VS Code workspace storage for open files."""
    open_files = []
    # Best effort — VS Code stores state in SQLite which we avoid depending on
    # Instead, look for workspace.json files
    for ws_dir in ws_storage.iterdir():
        if not ws_dir.is_dir():
            continue
        ws_json = ws_dir / "workspace.json"
        if ws_json.exists():
            try:
                data = json.loads(ws_json.read_text(encoding="utf-8"))
                folder = data.get("folder", "")
                if project_dir and folder != project_dir:
                    continue
                # Look for tabs/state in the workspace
                # This is a simplified approach
            except (json.JSONDecodeError, OSError):
                continue
    return open_files


def _capture_vim_state(project_dir: str, state: EditorState) -> EditorState:
    """Capture Vim/Neovim state from session/shada files."""
    # Check for Neovim shada file or Vim session
    shada_file = Path.home() / ".local" / "share" / "nvim" / "shada" / "main.shada"
    viminfo = Path.home() / ".viminfo"
    
    # Check for session files in project directory
    if project_dir:
        session_file = Path(project_dir) / "Session.vim"
        if session_file.exists():
            # Parse session file for open files
            open_files = _parse_vim_session(session_file)
            state.open_files = open_files

    return state


def _parse_vim_session(session_file: Path) -> List[OpenFile]:
    """Parse a Vim session file for open buffers/files."""
    open_files = []
    try:
        content = session_file.read_text(encoding="utf-8", errors="ignore")
        for line in content.split("\n"):
            line = line.strip()
            # Look for badd commands: badd +1 path/to/file
            if line.startswith("badd"):
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    filepath = parts[2]
                    open_files.append(OpenFile(path=filepath))
            # Also look for edit commands
            elif line.startswith("edit ") or line.startswith("e "):
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    filepath = parts[1].strip()
                    if filepath and not filepath.startswith("+"):
                        open_files.append(OpenFile(path=filepath))
    except OSError:
        pass
    return open_files


def _capture_jetbrains_state(project_dir: str, state: EditorState) -> EditorState:
    """Capture JetBrains IDE state (best effort)."""
    # JetBrains stores workspace state in .idea/workspace.xml
    if project_dir:
        workspace_xml = Path(project_dir) / ".idea" / "workspace.xml"
        if workspace_xml.exists():
            open_files = _parse_jetbrains_workspace(workspace_xml)
            state.open_files = open_files
    return state


def _parse_jetbrains_workspace(workspace_xml: Path) -> List[OpenFile]:
    """Parse JetBrains workspace.xml for open files (simplified)."""
    open_files = []
    try:
        content = workspace_xml.read_text(encoding="utf-8", errors="ignore")
        # Look for file:// URIs in the workspace
        import re
        matches = re.findall(r'file://(/[^"<\s]+)', content)
        seen = set()
        for match in matches:
            if match not in seen:
                seen.add(match)
                open_files.append(OpenFile(path=match))
    except OSError:
        pass
    return open_files


def restore_editor_state(state: EditorState, dry_run: bool = False) -> bool:
    """Attempt to restore editor state by opening files.
    
    Returns True if the editor was launched.
    """
    if dry_run:
        return True

    if not state.open_files:
        return True

    file_paths = [f.path for f in state.open_files if os.path.exists(f.path)]
    if not file_paths:
        return True

    editor_cmd = state.editor_type
    if editor_cmd == "vscode":
        cmd = "code"
    elif editor_cmd == "neovim":
        cmd = "nvim"
    elif editor_cmd == "vim":
        cmd = "vim"
    elif editor_cmd == "jetbrains":
        cmd = "idea"
    else:
        # Try common editors
        for candidate in ["code", "nvim", "vim", "nano"]:
            if shutil.which(candidate):
                cmd = candidate
                break
        else:
            return False

    try:
        # Launch editor with the files
        subprocess.Popen(
            [cmd] + file_paths,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except (OSError, FileNotFoundError):
        return False
