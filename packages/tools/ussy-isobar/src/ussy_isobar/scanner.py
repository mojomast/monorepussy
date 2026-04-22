"""Git history scanner — extracts commit data, file changes, and co-change patterns."""

import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class FileCommit:
    """A single commit touching a file."""
    commit_hash: str
    author: str
    timestamp: datetime
    message: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0

    @property
    def is_bug_fix(self) -> bool:
        bug_patterns = [
            r"\bfix\b", r"\bbug\b", r"\bpatch\b", r"\bhotfix\b",
            r"\bissue\b", r"\bresolve\b", r"\bclose\b",
        ]
        msg_lower = self.message.lower()
        return any(re.search(p, msg_lower) for p in bug_patterns)


@dataclass
class FileHistory:
    """Aggregated commit history for a single file."""
    filepath: str
    commits: List[FileCommit] = field(default_factory=list)

    @property
    def total_commits(self) -> int:
        return len(self.commits)

    @property
    def bug_fix_commits(self) -> List[FileCommit]:
        return [c for c in self.commits if c.is_bug_fix]

    @property
    def bug_fix_count(self) -> int:
        return len(self.bug_fix_commits)

    def commits_in_period(self, start: datetime, end: datetime) -> List[FileCommit]:
        return [c for c in self.commits if start <= c.timestamp <= end]

    def commits_per_week(self, num_weeks: int = 4, now: Optional[datetime] = None) -> float:
        """Average commits per week over the last num_weeks."""
        if now is None:
            now = datetime.now(timezone.utc)
        start = now - timedelta(weeks=num_weeks)
        recent = self.commits_in_period(start, now)
        if num_weeks == 0:
            return 0.0
        return len(recent) / num_weeks

    @property
    def last_commit_time(self) -> Optional[datetime]:
        if not self.commits:
            return None
        return max(c.timestamp for c in self.commits)

    @property
    def total_insertions(self) -> int:
        return sum(c.insertions for c in self.commits)

    @property
    def total_deletions(self) -> int:
        return sum(c.deletions for c in self.commits)


@dataclass
class ScanResult:
    """Complete scan result for a repository."""
    root: str
    file_histories: Dict[str, FileHistory] = field(default_factory=dict)
    co_changes: Dict[Tuple[str, str], int] = field(default_factory=dict)
    import_graph: Dict[str, Set[str]] = field(default_factory=dict)
    scan_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GitScanner:
    """Scans a git repository to extract commit history and file metadata."""

    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(self.repo_path):
            raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")

    def _run_git(self, args: List[str]) -> str:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def is_git_repo(self) -> bool:
        """Check if the path is inside a git repository."""
        output = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return output.strip() == "true"

    def get_commit_log(self, max_commits: int = 500) -> List[FileCommit]:
        """Parse git log into FileCommit objects."""
        # Format: hash|||author|||timestamp_iso|||subject|||files|||insertions|||deletions
        separator = "|||"
        log_format = separator.join([
            "%H", "%an", "%aI", "%s", "", "%aI"
        ])
        output = self._run_git([
            "log", f"--max-count={max_commits}",
            f"--format={separator.join(['%H', '%an', '%aI', '%s'])}",
            "--numstat",
        ])
        if not output:
            return []

        commits: List[FileCommit] = []
        current_hash = ""
        current_author = ""
        current_timestamp = datetime.now(timezone.utc)
        current_message = ""
        current_files: List[str] = []
        current_insertions = 0
        current_deletions = 0

        lines = output.split("\n")
        for line in lines:
            parts = line.split(separator)
            if len(parts) == 4:
                # New commit header
                if current_hash:
                    commits.append(FileCommit(
                        commit_hash=current_hash,
                        author=current_author,
                        timestamp=current_timestamp,
                        message=current_message,
                        files_changed=list(current_files),
                        insertions=current_insertions,
                        deletions=current_deletions,
                    ))
                current_hash = parts[0]
                current_author = parts[1]
                try:
                    current_timestamp = datetime.fromisoformat(parts[2].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    current_timestamp = datetime.now(timezone.utc)
                current_message = parts[3]
                current_files = []
                current_insertions = 0
                current_deletions = 0
            elif line.strip() and "\t" in line:
                # numstat line: insertions\tdeletions\tfilepath
                stat_parts = line.split("\t")
                if len(stat_parts) >= 3:
                    try:
                        ins = int(stat_parts[0]) if stat_parts[0] != "-" else 0
                        dele = int(stat_parts[1]) if stat_parts[1] != "-" else 0
                    except ValueError:
                        ins, dele = 0, 0
                    filepath = stat_parts[2]
                    current_files.append(filepath)
                    current_insertions += ins
                    current_deletions += dele

        # Don't forget the last commit
        if current_hash:
            commits.append(FileCommit(
                commit_hash=current_hash,
                author=current_author,
                timestamp=current_timestamp,
                message=current_message,
                files_changed=list(current_files),
                insertions=current_insertions,
                deletions=current_deletions,
            ))

        return commits

    def scan(self, max_commits: int = 500) -> ScanResult:
        """Perform a full scan of the repository."""
        result = ScanResult(root=self.repo_path)

        commits = self.get_commit_log(max_commits)
        if not commits:
            return result

        # Build file histories
        for commit in commits:
            for filepath in commit.files_changed:
                if filepath not in result.file_histories:
                    result.file_histories[filepath] = FileHistory(filepath=filepath)
                result.file_histories[filepath].commits.append(commit)

        # Build co-change map
        for commit in commits:
            files = commit.files_changed
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    pair = tuple(sorted([files[i], files[j]]))
                    result.co_changes[pair] = result.co_changes.get(pair, 0) + 1

        # Build import graph
        result.import_graph = self._scan_imports(result.file_histories.keys())

        return result

    def _scan_imports(self, filepaths) -> Dict[str, Set[str]]:
        """Scan Python files for import dependencies."""
        import_graph: Dict[str, Set[str]] = defaultdict(set)
        for filepath in filepaths:
            if not filepath.endswith(".py"):
                continue
            full_path = os.path.join(self.repo_path, filepath)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (OSError, IOError):
                continue

            for line in content.splitlines():
                line = line.strip()
                # Match "from X import Y" or "import X"
                m = re.match(r"^from\s+([a-zA-Z_][\w.]*)\s+import", line)
                if m:
                    imported = m.group(1).replace(".", "/") + ".py"
                    import_graph[filepath].add(imported)
                    continue
                m = re.match(r"^import\s+([a-zA-Z_][\w.]*)(?:\s+as\s+\w+)?$", line)
                if m:
                    imported = m.group(1).replace(".", "/") + ".py"
                    import_graph[filepath].add(imported)

        return dict(import_graph)
