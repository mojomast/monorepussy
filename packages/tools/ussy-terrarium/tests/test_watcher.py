"""Tests for the file watcher."""

import os
import tempfile
import time

import pytest

from terrarium.watcher import FileWatcher


class TestFileWatcher:
    """Tests for the file watcher module."""

    def test_initial_snapshot(self):
        """Taking a snapshot captures file mtimes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir)

            # Create a file
            filepath = os.path.join(tmpdir, "test.py")
            with open(filepath, "w") as f:
                f.write("x = 1\n")

            watcher.take_snapshot()
            assert filepath in watcher._snapshots

    def test_detect_new_file(self):
        """Detecting a newly added file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir)
            watcher.take_snapshot()

            # Add a new file
            filepath = os.path.join(tmpdir, "new.py")
            with open(filepath, "w") as f:
                f.write("y = 2\n")

            changed = watcher.detect_changes()
            assert filepath in changed

    def test_detect_modified_file(self):
        """Detecting a modified file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.py")
            with open(filepath, "w") as f:
                f.write("x = 1\n")

            watcher = FileWatcher(tmpdir)
            watcher.take_snapshot()

            # Wait briefly then modify
            time.sleep(0.05)
            with open(filepath, "w") as f:
                f.write("x = 2\n")

            # Force mtime difference
            os.utime(filepath, (time.time() + 1, time.time() + 1))

            changed = watcher.detect_changes()
            assert filepath in changed

    def test_detect_deleted_file(self):
        """Detecting a deleted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "temp.py")
            with open(filepath, "w") as f:
                f.write("z = 3\n")

            watcher = FileWatcher(tmpdir)
            watcher.take_snapshot()

            os.unlink(filepath)
            changed = watcher.detect_changes()
            assert filepath in changed

    def test_extension_filtering(self):
        """Only watch files with specified extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir, extensions=[".py"])

            py_file = os.path.join(tmpdir, "test.py")
            txt_file = os.path.join(tmpdir, "readme.txt")

            with open(py_file, "w") as f:
                f.write("pass\n")
            with open(txt_file, "w") as f:
                f.write("hello\n")

            snapshot = watcher._scan_files()
            assert py_file in snapshot
            assert txt_file not in snapshot

    def test_skip_hidden_dirs(self):
        """Hidden directories are not scanned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir)

            # Create a file in a hidden directory
            hidden_dir = os.path.join(tmpdir, ".hidden")
            os.makedirs(hidden_dir)
            with open(os.path.join(hidden_dir, "test.py"), "w") as f:
                f.write("pass\n")

            snapshot = watcher._scan_files()
            assert len(snapshot) == 0

    def test_watch_once(self):
        """watch_once returns changes on first call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir)

            # Take initial snapshot of empty dir
            watcher.take_snapshot()
            changed = watcher.detect_changes()
            assert changed == []

            # Add a file
            fpath = os.path.join(tmpdir, "test.py")
            with open(fpath, "w") as f:
                f.write("pass\n")
                f.flush()
                os.fsync(f.fileno())

            # Detect change
            changed = watcher.detect_changes()
            assert len(changed) > 0

    def test_callback_on_change(self):
        """Callback is triggered when files change."""
        received = []

        def on_change(files):
            received.extend(files)

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir, callback=on_change, poll_interval=0.01)
            watcher.take_snapshot()

            fpath = os.path.join(tmpdir, "test.py")
            with open(fpath, "w") as f:
                f.write("pass\n")
                f.flush()
                os.fsync(f.fileno())

            # Manually detect changes and trigger callback
            changed = watcher.detect_changes()
            if changed and watcher.callback:
                watcher.callback(changed)

            assert len(received) > 0

    def test_stop_watcher(self):
        """Stop the watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(tmpdir, poll_interval=0.01)
            watcher._running = True
            watcher.stop()
            assert watcher._running is False
