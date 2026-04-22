"""Fossil detection — find deleted code artifacts preserved in git history.

A Fossil is a code artifact (function, class, variable, import) that was
deleted at some point but exists in historical commits. Like paleontological
fossils, they tell us about the evolutionary history of the codebase.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from typing import List, Optional

from ussy_strata.core import Fossil


# Patterns for detecting code artifacts
_FUNCTION_PATTERNS = [
    # Python
    re.compile(r'^(\s*)def\s+(\w+)\s*\('),
    re.compile(r'^(\s*)async\s+def\s+(\w+)\s*\('),
    # JavaScript/TypeScript
    re.compile(r'^(\s*)function\s+(\w+)\s*\('),
    re.compile(r'^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()'),
    # Java/C/C++/Go/Rust
    re.compile(r'^(\s*)(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\('),
    # Go
    re.compile(r'^(\s*)func\s+(\w+)\s*\('),
    # Rust
    re.compile(r'^(\s*)fn\s+(\w+)\s*\('),
]

_CLASS_PATTERNS = [
    re.compile(r'^(\s*)class\s+(\w+)'),
    re.compile(r'^(\s*)struct\s+(\w+)'),
    re.compile(r'^(\s*)interface\s+(\w+)'),
    re.compile(r'^(\s*)enum\s+(\w+)'),
    re.compile(r'^(\s*)trait\s+(\w+)'),
    re.compile(r'^(\s*)impl\s+(\w+)'),
]

_IMPORT_PATTERNS = [
    re.compile(r'^import\s+([\w.]+)'),
    re.compile(r'^from\s+([\w.]+)\s+import'),
    re.compile(r'^#include\s*[<"]([^>"]+)'),
    re.compile(r'^use\s+([\w:]+)'),
]

_VARIABLE_PATTERNS = [
    re.compile(r'^(\s*)(?:const|let|var)\s+(\w+)'),
    re.compile(r'^(\s*)(\w+)\s*:\s*(?:\w+\s*)?='),
]


def _run_git(args: List[str], cwd: str) -> str:
    """Run a git command and return its stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _extract_artifacts(content: str, file_path: str) -> List[dict]:
    """Extract code artifacts from file content.

    Returns list of dicts with keys: name, kind, line_number, content
    """
    artifacts: List[dict] = []
    for lineno, line in enumerate(content.split("\n"), 1):
        # Functions
        for pat in _FUNCTION_PATTERNS:
            m = pat.match(line)
            if m:
                name = m.group(m.lastindex)
                artifacts.append({
                    "name": name,
                    "kind": "function",
                    "line_number": lineno,
                    "content": line.strip(),
                })
                break
        else:
            # Classes
            for pat in _CLASS_PATTERNS:
                m = pat.match(line)
                if m:
                    name = m.group(m.lastindex)
                    artifacts.append({
                        "name": name,
                        "kind": "class",
                        "line_number": lineno,
                        "content": line.strip(),
                    })
                    break
            else:
                # Imports
                for pat in _IMPORT_PATTERNS:
                    m = pat.match(line)
                    if m:
                        name = m.group(1)
                        artifacts.append({
                            "name": name,
                            "kind": "import",
                            "line_number": lineno,
                            "content": line.strip(),
                        })
                        break

    return artifacts


def _get_diff_deletions(repo_path: str, commit_hash: str) -> List[dict]:
    """Get deleted lines from a commit's diff.

    Returns list of dicts: {file_path, line, line_number}
    """
    try:
        output = _run_git(
            ["diff-tree", "-r", "--no-commit-id", "--diff-filter=D", commit_hash],
            cwd=repo_path,
        )
        deleted_files: List[str] = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                deleted_files.append(parts[-1])

        return [{"file_path": f, "line": "", "line_number": 0} for f in deleted_files]
    except RuntimeError:
        return []


def _get_file_at_commit(repo_path: str, commit_hash: str, file_path: str) -> Optional[str]:
    """Get file content at a specific commit."""
    try:
        return _run_git(
            ["show", f"{commit_hash}:{file_path}"],
            cwd=repo_path,
        )
    except RuntimeError:
        return None


def _get_parent_hash(repo_path: str, commit_hash: str) -> str:
    """Get the first parent hash of a commit."""
    try:
        output = _run_git(
            ["rev-parse", f"{commit_hash}^"],
            cwd=repo_path,
        )
        return output.strip()
    except RuntimeError:
        return ""


def _get_commit_date(repo_path: str, commit_hash: str) -> Optional[datetime]:
    """Get the author date of a commit."""
    try:
        output = _run_git(
            ["show", "-s", "--format=%aI", commit_hash],
            cwd=repo_path,
        )
        return datetime.fromisoformat(output.strip())
    except (RuntimeError, ValueError):
        return None


def excavate_fossils(
    repo_path: str,
    pattern: str = "",
    file_glob: str = "",
    max_commits: int = 0,
) -> List[Fossil]:
    """Find all fossils (deleted code artifacts) in the repository.

    Scans git history for deleted files and extracts code artifacts
    that were removed.

    Args:
        repo_path: Path to the git repository.
        pattern: Optional regex pattern to filter fossil names.
        file_glob: Optional file glob to limit search scope.
        max_commits: Max commits to scan (0 = all).

    Returns:
        List of Fossil objects.
    """
    fossils: List[Fossil] = []

    # Get commits that deleted files
    args = ["log", "--diff-filter=D", "--format=%H"]
    if file_glob:
        args.append(f"--{file_glob}")
    if max_commits > 0:
        args.append(f"--max-count={max_commits}")

    try:
        output = _run_git(args, cwd=repo_path)
    except RuntimeError:
        return fossils

    commit_hashes = [h.strip() for h in output.strip().split("\n") if h.strip()]

    pat_re = re.compile(pattern, re.IGNORECASE) if pattern else None

    for commit_hash in commit_hashes:
        # Get files deleted in this commit
        try:
            diff_output = _run_git(
                ["diff-tree", "-r", "--no-commit-id", "--diff-filter=D", commit_hash],
                cwd=repo_path,
            )
        except RuntimeError:
            continue

        for diff_line in diff_output.strip().split("\n"):
            if not diff_line.strip():
                continue
            parts = diff_line.split("\t")
            if len(parts) < 2:
                continue
            file_path = parts[-1]

            # Get file content from parent (before deletion)
            parent_hash = _get_parent_hash(repo_path, commit_hash)
            if not parent_hash:
                continue

            content = _get_file_at_commit(repo_path, parent_hash, file_path)
            if not content:
                continue

            # Extract artifacts from the file before deletion
            artifacts = _extract_artifacts(content, file_path)

            deposited_hash = _find_deposited_commit(
                repo_path, file_path, parent_hash
            )
            deposited_date = _get_commit_date(repo_path, deposited_hash) if deposited_hash else None
            extinct_date = _get_commit_date(repo_path, commit_hash)

            for art in artifacts:
                if pat_re and not pat_re.search(art["name"]):
                    continue

                fossil = Fossil(
                    name=art["name"],
                    kind=art["kind"],
                    file_path=file_path,
                    deposited_hash=deposited_hash or parent_hash,
                    deposited_date=deposited_date,
                    extinct_hash=commit_hash,
                    extinct_date=extinct_date,
                    content=art["content"],
                )
                fossils.append(fossil)

    return fossils


def _find_deposited_commit(
    repo_path: str, file_path: str, before_hash: str
) -> Optional[str]:
    """Find the commit where a file was first added (deposited)."""
    try:
        output = _run_git(
            ["log", "--diff-filter=A", "--format=%H", "--", file_path],
            cwd=repo_path,
        )
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        return lines[-1] if lines else None  # oldest add
    except RuntimeError:
        return None


def find_fossils_in_diff(
    repo_path: str,
    commit_hash: str,
) -> List[Fossil]:
    """Find fossils in a specific commit's diff.

    Examines deleted lines in the commit and extracts code artifacts.
    """
    fossils: List[Fossil] = []

    try:
        # Get the diff with deleted lines
        diff_output = _run_git(
            ["show", "--format=%H|%aI", "--no-color", commit_hash],
            cwd=repo_path,
        )
    except RuntimeError:
        return fossils

    # Parse the diff to find deleted lines with code artifacts
    current_file = ""
    for line in diff_output.split("\n"):
        # File header
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("--- "):
            pass
        elif line.startswith("-") and not line.startswith("---"):
            deleted_line = line[1:]
            for pat in _FUNCTION_PATTERNS:
                m = pat.match(deleted_line)
                if m:
                    name = m.group(m.lastindex)
                    extinct_date = _get_commit_date(repo_path, commit_hash)
                    fossils.append(Fossil(
                        name=name,
                        kind="function",
                        file_path=current_file,
                        deposited_hash="",
                        deposited_date=None,
                        extinct_hash=commit_hash,
                        extinct_date=extinct_date,
                        content=deleted_line.strip(),
                    ))
                    break
            else:
                for pat in _CLASS_PATTERNS:
                    m = pat.match(deleted_line)
                    if m:
                        name = m.group(m.lastindex)
                        extinct_date = _get_commit_date(repo_path, commit_hash)
                        fossils.append(Fossil(
                            name=name,
                            kind="class",
                            file_path=current_file,
                            deposited_hash="",
                            deposited_date=None,
                            extinct_hash=commit_hash,
                            extinct_date=extinct_date,
                            content=deleted_line.strip(),
                        ))
                        break

    return fossils
