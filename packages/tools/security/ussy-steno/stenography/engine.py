"""Core scanning engine — orchestrates all scanners over files and diffs."""

import os
import subprocess
import sys
from typing import Optional

from stenography.models import ScanResult, Finding
from stenography.scanners import (
    ZeroWidthScanner,
    HomoglyphScanner,
    RTLScanner,
    WhitespaceScanner,
    CommentScanner,
)

# File extensions to scan (source code files)
SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
    ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".html", ".css", ".scss", ".less", ".svg", ".xml",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sql", ".r", ".R", ".m", ".mm", ".lua", ".pl", ".pm",
    ".dart", ".vue", ".svelte",
    ".txt",  # fixtures and docs can contain steganographic content too
}

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".env",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".hg", ".svn", "target", "vendor", "Cargo_target",
}


class ScannerEngine:
    """Orchestrates all scanners over files and diffs."""

    def __init__(self, entropy_threshold: float = 0.8):
        self.zero_width = ZeroWidthScanner()
        self.homoglyph = HomoglyphScanner()
        self.rtl = RTLScanner()
        self.whitespace = WhitespaceScanner(entropy_threshold=entropy_threshold)
        self.comment = CommentScanner()
        self.scanners = [
            self.zero_width,
            self.homoglyph,
            self.rtl,
            self.whitespace,
            self.comment,
        ]

    def scan_path(self, path: str, extensions: Optional[set] = None) -> ScanResult:
        """Scan a file or directory path."""
        result = ScanResult()
        exts = extensions or SCAN_EXTENSIONS

        if os.path.isfile(path):
            self._scan_file(path, result)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                # Skip unwanted directories
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    _, ext = os.path.splitext(fname)
                    if ext.lower() in exts or not exts:
                        self._scan_file(fpath, result)
        else:
            print(f"Warning: path not found: {path}", file=sys.stderr)

        return result

    def scan_diff(self, diff_ref: str) -> ScanResult:
        """Scan only lines changed in a git diff.

        For a commit ref (e.g. HEAD~1, abc123) we use 'git show' to get the
        diff introduced by that commit.  For range syntax (a..b, a...b) we
        use 'git diff' as before.  Falls back to the working-tree diff
        (git diff <ref>) only when the show/range command returns nothing.
        """
        result = ScanResult()
        cwd = os.getcwd()

        # Choose the right git command based on the ref format
        is_range = ".." in diff_ref
        if is_range:
            primary_cmd = ["git", "diff", diff_ref]
        else:
            # 'git show' gives the diff of a single commit; works for HEAD~1 etc.
            primary_cmd = ["git", "show", "--format=\"\"", diff_ref]

        try:
            proc = subprocess.run(
                primary_cmd,
                capture_output=True, text=True, timeout=30,
            )
            diff_text = proc.stdout

            if proc.returncode != 0:
                print(f"Warning: git command failed: {proc.stderr.strip()}", file=sys.stderr)
                return result

            # Fallback: working-tree diff (unstaged changes against ref)
            if not diff_text.strip():
                fallback = subprocess.run(
                    ["git", "diff", diff_ref],
                    capture_output=True, text=True, timeout=30,
                )
                diff_text = fallback.stdout

        except FileNotFoundError:
            print("Error: git not found. diff command requires git.", file=sys.stderr)
            return result
        except subprocess.TimeoutExpired:
            print("Error: git command timed out.", file=sys.stderr)
            return result

        # Parse diff to get changed lines per file
        changed_lines = self._parse_diff(diff_text, cwd)

        for file_path, line_numbers in changed_lines.items():
            if not os.path.isfile(file_path):
                continue
            self._scan_file_lines(file_path, line_numbers, result)

        return result

    def scan_stdin(self) -> ScanResult:
        """Scan content from stdin."""
        result = ScanResult()
        content = sys.stdin.read()
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            for scanner in self.scanners:
                findings = scanner.scan_line("<stdin>", i, line)
                for f in findings:
                    result.add(f)
        result.files_scanned = 1
        return result

    def _scan_file(self, file_path: str, result: ScanResult):
        """Scan a single file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, IOError) as e:
            print(f"Warning: cannot read {file_path}: {e}", file=sys.stderr)
            return

        for i, line in enumerate(lines, 1):
            for scanner in self.scanners:
                findings = scanner.scan_line(file_path, i, line.rstrip("\n\r"))
                for finding in findings:
                    result.add(finding)

        result.files_scanned += 1

    def _scan_file_lines(self, file_path: str, line_numbers: set, result: ScanResult):
        """Scan specific lines in a file (for diff mode)."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, IOError) as e:
            print(f"Warning: cannot read {file_path}: {e}", file=sys.stderr)
            return

        for line_num in line_numbers:
            if 1 <= line_num <= len(lines):
                line = lines[line_num - 1].rstrip("\n\r")
                for scanner in self.scanners:
                    findings = scanner.scan_line(file_path, line_num, line)
                    for finding in findings:
                        result.add(finding)

        result.files_scanned += 1

    def _parse_diff(self, diff_text: str, repo_root: str) -> dict:
        """Parse unified diff output to get {file: set(line_numbers)}.

        File paths are resolved relative to repo_root and validated to
        prevent path-traversal outside the project directory.
        """
        result = {}
        current_file = None
        current_line = 0
        in_hunk = False
        repo_root_real = os.path.realpath(repo_root)

        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                rel_path = line[6:]
                # Resolve and guard against traversal
                candidate = os.path.realpath(os.path.join(repo_root, rel_path))
                if not candidate.startswith(repo_root_real + os.sep) and candidate != repo_root_real:
                    current_file = None
                    in_hunk = False
                    continue
                current_file = candidate
                result[current_file] = set()
                in_hunk = False
            elif line.startswith("@@"):
                # Parse @@ -a,b +c,d @@
                parts = line.split("+")
                if len(parts) >= 2:
                    range_part = parts[1].split(",")[0].strip()
                    range_part = range_part.split("@")[0].strip()
                    try:
                        current_line = int(range_part)
                    except ValueError:
                        current_line = 1
                in_hunk = True
            elif in_hunk and current_file:
                if line.startswith("+"):
                    result[current_file].add(current_line)
                    current_line += 1
                elif line.startswith("-"):
                    pass
                elif not line.startswith("\\"):
                    current_line += 1

        return result
