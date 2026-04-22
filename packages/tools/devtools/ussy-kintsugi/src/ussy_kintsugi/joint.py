"""Joint data model and storage for golden joints."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


# Default storage location
KINTSUGI_DIR = ".kintsugi"
JOINTS_FILE = "joints.jsonl"


def _generate_joint_id(timestamp: datetime, bug_ref: str) -> str:
    """Generate a unique joint ID like 'j-20240315-proj892'."""
    date_str = timestamp.strftime("%Y%m%d")
    # Normalize bug_ref: lowercase, remove non-alnum
    slug = re.sub(r"[^a-zA-Z0-9]", "", bug_ref).lower()
    return f"j-{date_str}-{slug}"


@dataclass
class Joint:
    """A golden joint marking a bug repair site."""

    id: str = ""
    file: str = ""
    line: int = 0
    timestamp: str = ""
    bug_ref: str = ""
    severity: str = "warning"  # critical | warning | info
    break_description: str = ""
    repair_description: str = ""
    removal_impact: str = ""
    test_ref: str = ""
    status: str = "solid_gold"  # solid_gold | hollow | untested
    last_stress_tested: str = ""

    def __post_init__(self):
        if not self.id:
            ts = (
                datetime.fromisoformat(self.timestamp)
                if self.timestamp
                else datetime.now(timezone.utc)
            )
            self.id = _generate_joint_id(ts, self.bug_ref or "unknown")
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Serialize joint to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Joint":
        """Deserialize joint from a dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_jsonl(self) -> str:
        """Serialize to a single JSON line."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


class JointStore:
    """Persistent storage for golden joints using JSONL format."""

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root) if root else Path.cwd()
        self.dir = self.root / KINTSUGI_DIR
        self.path = self.dir / JOINTS_FILE

    def _ensure_dir(self):
        self.dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> List[Joint]:
        """Load all joints from the JSONL file."""
        if not self.path.exists():
            return []
        joints = []
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    joints.append(Joint.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        return joints

    def save(self, joint: Joint) -> Joint:
        """Append a joint to the store."""
        self._ensure_dir()
        with open(self.path, "a") as f:
            f.write(joint.to_jsonl() + "\n")
        return joint

    def save_all(self, joints: List[Joint]):
        """Overwrite the store with the given joints."""
        self._ensure_dir()
        with open(self.path, "w") as f:
            for j in joints:
                f.write(j.to_jsonl() + "\n")

    def update(self, joint_id: str, **kwargs) -> Optional[Joint]:
        """Update a joint by ID with given fields."""
        joints = self.load_all()
        for i, j in enumerate(joints):
            if j.id == joint_id:
                for k, v in kwargs.items():
                    if hasattr(j, k):
                        setattr(j, k, v)
                joints[i] = j
                self.save_all(joints)
                return j
        return None

    def delete(self, joint_id: str) -> bool:
        """Delete a joint by ID. Returns True if found and deleted."""
        joints = self.load_all()
        new_joints = [j for j in joints if j.id != joint_id]
        if len(new_joints) < len(joints):
            self.save_all(new_joints)
            return True
        return False

    def find_by_file(self, file_path: str) -> List[Joint]:
        """Find all joints for a given file path."""
        return [j for j in self.load_all() if j.file == file_path]

    def find_by_id(self, joint_id: str) -> Optional[Joint]:
        """Find a joint by its ID."""
        for j in self.load_all():
            if j.id == joint_id:
                return j
        return None

    def find_by_bug_ref(self, bug_ref: str) -> List[Joint]:
        """Find all joints for a given bug reference."""
        return [j for j in self.load_all() if j.bug_ref == bug_ref]

    def find_hollow(self) -> List[Joint]:
        """Find all hollow joints (repairs that can potentially be removed)."""
        return [j for j in self.load_all() if j.status == "hollow"]
