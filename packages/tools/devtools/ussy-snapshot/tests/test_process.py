"""Tests for process state capture and restart."""

import os
from unittest.mock import patch, MagicMock

from ussy_snapshot.process import (
    capture_processes,
    restart_process,
    restart_processes,
    is_process_running,
    stop_process,
)
from ussy_snapshot.models import ProcessRecord


class TestCaptureProcesses:
    def test_returns_list(self):
        processes = capture_processes()
        assert isinstance(processes, list)

    def test_process_records_have_fields(self):
        processes = capture_processes()
        for p in processes:
            assert isinstance(p, ProcessRecord)
            assert p.pid > 0
            assert p.command != ""

    def test_excludes_own_pid(self):
        """Should not include our own process."""
        processes = capture_processes()
        own_pid = os.getpid()
        for p in processes:
            assert p.pid != own_pid


class TestRestartProcess:
    def test_restart_empty_command(self):
        record = ProcessRecord(pid=1, command="", startup_command="")
        result = restart_process(record)
        assert result is False

    def test_restart_dry_run(self):
        record = ProcessRecord(pid=1, command="echo", startup_command="echo hello")
        result = restart_process(record, dry_run=True)
        assert result is True

    def test_restart_with_command(self):
        record = ProcessRecord(
            pid=9999,
            command="echo",
            startup_command="echo test",
            auto_restart=True,
        )
        # This should actually work — echo exits immediately
        result = restart_process(record)
        assert result is True


class TestRestartProcesses:
    def test_restart_multiple(self):
        records = [
            ProcessRecord(pid=1, startup_command="echo a", auto_restart=True),
            ProcessRecord(pid=2, startup_command="echo b", auto_restart=True),
            ProcessRecord(pid=3, startup_command="echo c", auto_restart=False),
        ]
        results = restart_processes(records)
        # Only auto_restart=True should be restarted
        assert "echo a" in results
        assert "echo b" in results
        assert "echo c" not in results

    def test_restart_empty(self):
        results = restart_processes([])
        assert results == {}


class TestIsProcessRunning:
    def test_own_process_is_running(self):
        assert is_process_running(os.getpid()) is True

    def test_nonexistent_process(self):
        assert is_process_running(999999999) is False


class TestStopProcess:
    def test_stop_nonexistent(self):
        result = stop_process(999999999)
        assert result is False
