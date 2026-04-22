"""Workspace branching — fork your exploration state.

Branches let you fork your working context so you can explore an
alternative approach without losing your current state.  Think of it as
``git branch`` for your brain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ussy_mushin.journal import Journal, JournalEntry
from ussy_mushin.storage import (
    BRANCHES_FILE,
    WORKSPACES_DIR,
    _ensure_subdir,
    atomic_write_json,
    mushin_root,
    read_json,
    ts_now,
)
from ussy_mushin.workspace import Workspace, _generate_id, list_workspaces


@dataclass
class Branch:
    """A lightweight reference from a parent workspace to a child."""

    name: str
    workspace_id: str = ""
    parent_id: str = ""
    created_at: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = ts_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "workspace_id": self.workspace_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Branch:
        return cls(
            name=data["name"],
            workspace_id=data.get("workspace_id", ""),
            parent_id=data.get("parent_id", ""),
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
        )


class BranchManager:
    """Manage workspace branches within a project."""

    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self._branches: dict[str, Branch] = {}
        self._load()

    # -- persistence ----------------------------------------------------------

    @property
    def _path(self) -> Path:
        root = mushin_root(self.project_dir)
        return root / BRANCHES_FILE

    def _load(self) -> None:
        data = read_json(self._path)
        if data and isinstance(data, list):
            for b in data:
                branch = Branch.from_dict(b)
                self._branches[branch.name] = branch

    def save(self) -> None:
        atomic_write_json(
            self._path, [b.to_dict() for b in self._branches.values()]
        )

    # -- operations -----------------------------------------------------------

    def create_branch(
        self,
        name: str,
        parent_workspace_id: str,
        description: str = "",
    ) -> Workspace:
        """Fork *parent_workspace_id* into a new workspace on branch *name*.

        The new workspace inherits the parent's journal entries and
        objects, but diverges from this point forward.
        """
        if name in self._branches:
            raise ValueError(f"Branch '{name}' already exists")

        # Load parent workspace
        parent = Workspace.load(self.project_dir, parent_workspace_id)

        # Create child workspace
        child = Workspace.create(
            self.project_dir,
            name=f"{parent.meta.name}:{name}",
            description=description or f"Branch '{name}' from {parent.meta.name}",
            parent_id=parent_workspace_id,
            branch_name=name,
        )

        # Copy journal entries from parent
        for entry in parent.journal.entries:
            child.journal.record(
                expression=entry.expression,
                output=entry.output,
                result_type=entry.result_type,
                context=entry.context,
            )

        # Copy objects from parent
        for key in parent.list_objects():
            try:
                obj = parent.load_object(key)
                child.save_object(key, obj)
            except (KeyError, Exception):
                pass

        child.save()

        # Record the branch
        branch = Branch(
            name=name,
            workspace_id=child.id,
            parent_id=parent_workspace_id,
            description=description,
        )
        self._branches[name] = branch
        self.save()

        return child

    def get_branch(self, name: str) -> Branch | None:
        return self._branches.get(name)

    def list_branches(self) -> list[Branch]:
        return list(self._branches.values())

    def delete_branch(self, name: str) -> bool:
        """Remove a branch reference (does *not* delete the workspace)."""
        if name not in self._branches:
            return False
        del self._branches[name]
        self.save()
        return True

    def rename_branch(self, old_name: str, new_name: str) -> bool:
        if old_name not in self._branches:
            return False
        if new_name in self._branches:
            raise ValueError(f"Branch '{new_name}' already exists")
        branch = self._branches.pop(old_name)
        branch.name = new_name
        self._branches[new_name] = branch
        self.save()
        return True

    def get_workspace_for_branch(self, name: str) -> Workspace | None:
        """Load the workspace associated with branch *name*."""
        branch = self._branches.get(name)
        if branch is None:
            return None
        return Workspace.load(self.project_dir, branch.workspace_id)
