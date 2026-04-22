from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

from .models import Mark


def marks_path(repo_path: str | Path) -> Path:
    return Path(repo_path) / ".reverseoracle" / "marks.json"


def ensure_repo_dir(repo_path: str | Path) -> Path:
    root = Path(repo_path) / ".reverseoracle"
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_marks(repo_path: str | Path) -> list[Mark]:
    path = marks_path(repo_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [Mark(**item) for item in data]


def save_marks(repo_path: str | Path, marks: list[Mark]) -> None:
    ensure_repo_dir(repo_path)
    marks_path(repo_path).write_text(json.dumps([m.to_dict() for m in marks], indent=2))


def add_mark(
    repo_path: str | Path,
    commit: str,
    description: str,
    alternative: str,
    module_path: str | None = None,
) -> Mark:
    mark = Mark(
        id=str(uuid4()),
        commit=commit,
        description=description,
        alternative=alternative,
        module_path=module_path,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    marks = load_marks(repo_path)
    marks.append(mark)
    save_marks(repo_path, marks)
    return mark


def lookup_mark(
    repo_path: str | Path, mark_id: str | None = None, commit: str | None = None
) -> Mark | None:
    for mark in load_marks(repo_path):
        if mark_id and mark.id == mark_id:
            return mark
        if commit and mark.commit == commit:
            return mark
    return None
