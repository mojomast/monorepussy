"""Process state capture and restart."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
from typing import List, Optional

from .models import ProcessRecord


def capture_processes() -> List[ProcessRecord]:
    """Capture running processes relevant to the development environment.
    
    Captures processes that appear to be development-related:
    servers, watchers, REPLs, build tools, etc.
    """
    processes = []
    try:
        result = subprocess.run(
            ["ps", "-o", "pid,command", "--no-headers"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return processes

        dev_keywords = {
            "python", "node", "npm", "yarn", "pnpm", "ruby", "rails",
            "java", "go ", "cargo", "rustc", "make", "webpack",
            "vite", "gulp", "grunt", "docker", "redis", "postgres",
            "mysql", "mongod", "celery", "flower", "uvicorn", "gunicorn",
            "flask", "django", "pytest", "jest", "mocha", "watch",
            "serve", "dev", "run", "start", "http", "api", "server",
            "nvim", "vim", "code", "tmux", "ssh", "mongod",
        }

        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split(None, 1)
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            cmd = parts[1]
            
            # Skip our own process and very short-lived commands
            if pid == os.getpid():
                continue
            if pid == os.getppid():
                continue

            # Check if this looks like a dev process
            cmd_lower = cmd.lower()
            is_dev = any(kw in cmd_lower for kw in dev_keywords)
            
            if is_dev:
                proc = ProcessRecord(
                    pid=pid,
                    command=cmd.split()[0] if cmd.split() else cmd,
                    arguments=cmd.split()[1:] if len(cmd.split()) > 1 else [],
                    startup_command=cmd,
                    auto_restart=False,
                )
                processes.append(proc)

    except (subprocess.TimeoutExpired, OSError):
        pass

    return processes


def restart_process(record: ProcessRecord, dry_run: bool = False) -> bool:
    """Attempt to restart a recorded process.
    
    Returns True if the process was started successfully.
    """
    if dry_run:
        return True

    cmd = record.startup_command or record.command
    if not cmd:
        return False

    try:
        cwd = record.working_directory if record.working_directory and os.path.isdir(record.working_directory) else None
        env = os.environ.copy()
        env.update(record.environment)
        
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except (OSError, FileNotFoundError):
        return False


def restart_processes(records: List[ProcessRecord], dry_run: bool = False) -> dict:
    """Attempt to restart all recorded processes.
    
    Returns a dict mapping startup_command -> success (bool).
    """
    results = {}
    for record in records:
        if record.auto_restart:
            results[record.startup_command] = restart_process(record, dry_run)
    return results


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Process exists but we can't signal it


def stop_process(pid: int) -> bool:
    """Attempt to gracefully stop a process by PID."""
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False
