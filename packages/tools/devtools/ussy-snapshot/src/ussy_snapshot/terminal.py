"""Terminal state capture and restore."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Optional

from .models import TerminalState


def capture_terminals() -> List[TerminalState]:
    """Capture state of all detected terminal sessions.
    
    Detects tmux sessions, screen sessions, and the current terminal.
    Returns a list of TerminalState objects.
    """
    terminals = []

    # Capture current terminal
    current = _capture_current_terminal()
    if current:
        terminals.append(current)

    # Capture tmux sessions if available
    if shutil.which("tmux"):
        terminals.extend(_capture_tmux_sessions())

    return terminals


def _capture_current_terminal() -> Optional[TerminalState]:
    """Capture the current terminal state."""
    cwd = os.getcwd()
    env = _get_relevant_env_vars()
    history = _get_shell_history()
    processes = _get_child_processes()
    buffer_text = _get_screen_buffer()
    fg_cmd = _get_foreground_command()

    return TerminalState(
        session_id="current",
        working_directory=cwd,
        environment=env,
        command_history=history,
        running_processes=processes,
        screen_buffer=buffer_text,
        foreground_command=fg_cmd,
    )


def _capture_tmux_sessions() -> List[TerminalState]:
    """Capture all tmux pane states."""
    sessions = []
    try:
        # List tmux sessions
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return sessions

        for session_name in result.stdout.strip().split("\n"):
            if not session_name:
                continue
            try:
                # List panes in this session
                pane_result = subprocess.run(
                    ["tmux", "list-panes", "-t", session_name, "-F",
                     "#{pane_id}:#{pane_current_path}:#{pane_current_command}"],
                    capture_output=True, text=True, timeout=5
                )
                if pane_result.returncode != 0:
                    continue
                for line in pane_result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split(":", 2)
                    pane_id = parts[0] if len(parts) > 0 else ""
                    pane_path = parts[1] if len(parts) > 1 else ""
                    pane_cmd = parts[2] if len(parts) > 2 else ""

                    # Capture pane content
                    buffer_text = ""
                    try:
                        buf_result = subprocess.run(
                            ["tmux", "capture-pane", "-t", pane_id, "-p", "-S", "-50"],
                            capture_output=True, text=True, timeout=5
                        )
                        if buf_result.returncode == 0:
                            buffer_text = buf_result.stdout
                    except (subprocess.TimeoutExpired, OSError):
                        pass

                    sessions.append(TerminalState(
                        session_id=f"tmux:{session_name}:{pane_id}",
                        working_directory=pane_path,
                        foreground_command=pane_cmd,
                        screen_buffer=buffer_text,
                    ))
            except (subprocess.TimeoutExpired, OSError):
                continue
    except (subprocess.TimeoutExpired, OSError):
        pass

    return sessions


def _get_relevant_env_vars() -> dict:
    """Get project-relevant environment variables (exclude secrets)."""
    secret_patterns = {"KEY", "SECRET", "PASSWORD", "TOKEN", "AUTH", "CREDENTIAL", "PRIVATE"}
    env = {}
    for key, value in os.environ.items():
        # Skip secrets
        if any(pattern in key.upper() for pattern in secret_patterns):
            continue
        # Skip very long values (likely encoded data)
        if len(value) > 500:
            continue
        env[key] = value
    return env


def _get_shell_history() -> List[str]:
    """Get recent shell command history."""
    history = []
    # Try bash history
    bash_hist = os.path.expanduser("~/.bash_history")
    if os.path.exists(bash_hist):
        try:
            with open(bash_hist, "r", errors="ignore") as f:
                lines = f.readlines()
                history.extend(line.strip() for line in lines[-100:] if line.strip())
        except OSError:
            pass
    # Try zsh history
    zsh_hist = os.path.expanduser("~/.zsh_history")
    if os.path.exists(zsh_hist):
        try:
            with open(zsh_hist, "r", errors="ignore") as f:
                lines = f.readlines()
                history.extend(line.strip() for line in lines[-100:] if line.strip())
        except OSError:
            pass
    return history[-50:]  # Keep last 50


def _get_child_processes() -> List[dict]:
    """Get child processes of the current terminal."""
    processes = []
    try:
        result = subprocess.run(
            ["ps", "-o", "pid,command", "--no-headers"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n")[:50]:
                parts = line.strip().split(None, 1)
                if len(parts) >= 2:
                    processes.append({
                        "pid": int(parts[0]),
                        "command": parts[1],
                    })
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass
    return processes


def _get_screen_buffer() -> str:
    """Try to get the terminal screen buffer (best effort)."""
    # Can't reliably get current terminal buffer without special support
    return ""


def _get_foreground_command() -> str:
    """Get the foreground command of the current terminal."""
    try:
        result = subprocess.run(
            ["ps", "-o", "comm=", "-p", str(os.getppid())],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def restore_terminal(state: TerminalState, dry_run: bool = False) -> bool:
    """Attempt to restore a terminal state.
    
    For tmux sessions, creates a new pane/window.
    For the current terminal, changes directory.
    
    Returns True if successful.
    """
    if dry_run:
        return True

    if state.session_id.startswith("tmux:"):
        return _restore_tmux_pane(state)
    else:
        return _restore_current_terminal(state)


def _restore_tmux_pane(state: TerminalState) -> bool:
    """Restore a tmux pane."""
    if not shutil.which("tmux"):
        return False
    try:
        # Create a new window in the tmux session
        parts = state.session_id.split(":")
        session_name = parts[1] if len(parts) > 1 else ""
        if not session_name:
            return False
        subprocess.run(
            ["tmux", "new-window", "-t", session_name, "-c", state.working_directory],
            capture_output=True, timeout=5
        )
        # If there was a foreground command, send it
        if state.foreground_command:
            subprocess.run(
                ["tmux", "send-keys", state.foreground_command, "Enter"],
                capture_output=True, timeout=5
            )
        return True
    except (subprocess.TimeoutExpired, OSError):
        return False


def _restore_current_terminal(state: TerminalState) -> bool:
    """Restore current terminal (change directory)."""
    if state.working_directory and os.path.isdir(state.working_directory):
        try:
            os.chdir(state.working_directory)
            return True
        except OSError:
            return False
    return True
