from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
from typing import Iterable

from .models import DecisionContext


TEST_PATTERNS = (
    re.compile(r"(^|/)test_.*\.py$"),
    re.compile(r"(^|/).*_test\.py$"),
    re.compile(r"\.test\.[^.]+$"),
)


def run_git(repo_path: str | Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo_path), check=True, capture_output=True, text=True
    )
    return result.stdout


def changed_files(repo_path: str | Path, commit_hash: str) -> list[str]:
    output = run_git(
        repo_path,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        commit_hash,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def file_at_commit(repo_path: str | Path, commit_hash: str, file_path: str) -> str:
    try:
        return run_git(repo_path, "show", f"{commit_hash}:{file_path}")
    except subprocess.CalledProcessError:
        return ""


def collect_dependencies(repo_path: str | Path, commit_hash: str) -> list[str]:
    deps: set[str] = set()
    for candidate in ("requirements.txt", "pyproject.toml", "package.json"):
        contents = file_at_commit(repo_path, commit_hash, candidate)
        if not contents:
            continue
        if candidate == "requirements.txt":
            for line in contents.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.add(line.split("==")[0].split(">=")[0].split("<=")[0].strip())
        elif candidate == "pyproject.toml":
            for line in contents.splitlines():
                m = re.match(r'\s*([A-Za-z0-9_.-]+)\s*=\s*"([^"]+)"', line)
                if m and m.group(1) in {"name", "version"}:
                    continue
            for match in re.finditer(
                r'"([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?(?:[<>=!~].*?)?"', contents
            ):
                value = match.group(1)
                if value not in {"python"}:
                    deps.add(value)
        elif candidate == "package.json":
            try:
                parsed = json.loads(contents)
            except json.JSONDecodeError:
                continue
            for section in ("dependencies", "devDependencies"):
                for dep in parsed.get(section, {}):
                    deps.add(dep)
    return sorted(deps)


def is_test_file(path: str) -> bool:
    return any(pattern.search(path) for pattern in TEST_PATTERNS)


def infer_interface_files(files: Iterable[str]) -> list[str]:
    interface_files: list[str] = []
    for file_path in files:
        if is_test_file(file_path):
            continue
        if Path(file_path).suffix in {".py", ".pyi", ".ts", ".tsx", ".js", ".jsx"}:
            interface_files.append(file_path)
    return interface_files


def reconstruct_context(
    repo_path: str | Path,
    commit_hash: str,
    description: str,
    alternative: str,
    module_path: str | None = None,
) -> DecisionContext:
    changed = changed_files(repo_path, commit_hash)
    files = changed if changed else ([module_path] if module_path else [])
    if module_path:
        files = [f for f in files if f.startswith(module_path)] or [module_path]
    interface_files = infer_interface_files(files)
    test_files = [path for path in changed if is_test_file(path)]
    if module_path and not test_files:
        test_files = [
            path for path in changed_files(repo_path, commit_hash) if is_test_file(path)
        ]
    file_contents = {
        path: file_at_commit(repo_path, commit_hash, path) for path in interface_files
    }
    test_contents = {
        path: file_at_commit(repo_path, commit_hash, path) for path in test_files
    }
    requirements_text = commit_message(repo_path, commit_hash)
    dependencies = collect_dependencies(repo_path, commit_hash)
    return DecisionContext(
        commit_hash=commit_hash,
        description=description,
        alternative=alternative,
        interface_files=interface_files,
        test_files=test_files,
        dependencies=dependencies,
        requirements_text=requirements_text,
        file_contents=file_contents,
        test_contents=test_contents,
    )


def commit_message(repo_path: str | Path, commit_hash: str) -> str:
    try:
        return run_git(
            repo_path, "log", "--format=%s%n%b", f"{commit_hash}^..{commit_hash}"
        )
    except subprocess.CalledProcessError:
        return run_git(repo_path, "show", "-s", "--format=%s%n%b", commit_hash)
