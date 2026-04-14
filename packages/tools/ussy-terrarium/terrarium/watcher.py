"""File watcher — monitor file changes and trigger metric recalculation."""

import os
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set


class FileWatcher:
    """Simple file watcher using polling (no external dependencies).

    Watches a directory tree for file modifications and triggers
    callbacks when changes are detected.
    """

    def __init__(
        self,
        root_path: str,
        callback: Optional[Callable[[List[str]], None]] = None,
        poll_interval: float = 1.0,
        extensions: Optional[List[str]] = None,
    ) -> None:
        self.root_path = os.path.abspath(root_path)
        self.callback = callback
        self.poll_interval = poll_interval
        self.extensions = extensions or [".py"]
        self._snapshots: Dict[str, float] = {}
        self._running = False

    def _should_watch(self, filepath: str) -> bool:
        """Check if a file should be watched based on extensions."""
        return any(filepath.endswith(ext) for ext in self.extensions)

    def _scan_files(self) -> Dict[str, float]:
        """Scan the directory and get modification times."""
        files = {}
        skip_dirs = {".git", "__pycache__", "node_modules", ".tox", ".mypy_cache", ".pytest_cache", "venv", ".venv"}

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
            for f in filenames:
                if self._should_watch(f):
                    filepath = os.path.join(dirpath, f)
                    try:
                        mtime = os.path.getmtime(filepath)
                        files[filepath] = mtime
                    except OSError:
                        continue
        return files

    def take_snapshot(self) -> None:
        """Take an initial snapshot of all file modification times."""
        self._snapshots = self._scan_files()

    def detect_changes(self) -> List[str]:
        """Detect files that have changed since the last snapshot.

        Returns:
            List of file paths that were added or modified.
        """
        current = self._scan_files()
        changed = []

        # Modified files
        for filepath, mtime in current.items():
            if filepath not in self._snapshots:
                changed.append(filepath)
            elif mtime > self._snapshots[filepath]:
                changed.append(filepath)

        # Deleted files
        for filepath in self._snapshots:
            if filepath not in current:
                changed.append(filepath)

        self._snapshots = current
        return changed

    def watch_once(self) -> List[str]:
        """Perform a single watch cycle.

        Returns:
            List of changed file paths.
        """
        if not self._snapshots:
            self.take_snapshot()
            return []
        return self.detect_changes()

    def watch_loop(self, max_iterations: Optional[int] = None) -> None:
        """Run the watch loop continuously.

        Args:
            max_iterations: Maximum number of poll cycles. None for infinite.
        """
        self._running = True
        self.take_snapshot()

        iteration = 0
        while self._running:
            if max_iterations is not None and iteration >= max_iterations:
                break

            changed = self.detect_changes()
            if changed and self.callback:
                try:
                    self.callback(changed)
                except Exception:
                    pass

            time.sleep(self.poll_interval)
            iteration += 1

    def stop(self) -> None:
        """Stop the watch loop."""
        self._running = False
