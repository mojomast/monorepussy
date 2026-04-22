"""Scar map — generate visual maps of golden joint density across the codebase."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .joint import Joint, JointStore


SEVERITY_ICONS = {"critical": "🔴", "warning": "🟡", "info": "🔵"}

TORII = "⛩️"


@dataclass
class FileScarInfo:
    """Scar information for a single file."""

    file: str = ""
    joints: List[Joint] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.joints)

    @property
    def critical_count(self) -> int:
        return sum(1 for j in self.joints if j.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for j in self.joints if j.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for j in self.joints if j.severity == "info")

    @property
    def hollow_count(self) -> int:
        return sum(1 for j in self.joints if j.status == "hollow")

    @property
    def solid_count(self) -> int:
        return sum(1 for j in self.joints if j.status == "solid_gold")


@dataclass
class DirectoryScarInfo:
    """Scar information for a directory."""

    path: str = ""
    files: List[FileScarInfo] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(f.total for f in self.files)

    @property
    def critical_count(self) -> int:
        return sum(f.critical_count for f in self.files)


def build_scar_map(
    root: Optional[str] = None,
    joints: Optional[List[Joint]] = None,
) -> Dict[str, FileScarInfo]:
    """Build a map of file → scar info from the joint store.

    Args:
        root: Repository root path (for the joint store).
        joints: Optional pre-loaded list of joints.

    Returns:
        Dictionary mapping file paths to their scar info.
    """
    if joints is None:
        store = JointStore(root)
        joints = store.load_all()

    file_map: Dict[str, FileScarInfo] = {}
    for j in joints:
        if j.file not in file_map:
            file_map[j.file] = FileScarInfo(file=j.file)
        file_map[j.file].joints.append(j)

    return file_map


def group_by_directory(
    file_map: Dict[str, FileScarInfo],
) -> Dict[str, DirectoryScarInfo]:
    """Group file scar info by directory."""
    dir_map: Dict[str, DirectoryScarInfo] = {}
    for file_path, info in file_map.items():
        dir_name = str(Path(file_path).parent)
        if dir_name not in dir_map:
            dir_map[dir_name] = DirectoryScarInfo(path=dir_name)
        dir_map[dir_name].files.append(info)
    return dir_map


def format_scar_map(
    file_map: Dict[str, FileScarInfo],
    root: Optional[str] = None,
) -> str:
    """Format the scar map as a human-readable string.

    Output example:
        src/auth/
          ├── login.py          ⛩️⛩️⛩️  3 joints (2 critical, 1 warning)
          └── session.py                   (intact)
    """
    dir_map = group_by_directory(file_map)
    lines = []

    # Sort directories for consistent output
    for dir_path in sorted(dir_map.keys()):
        dir_info = dir_map[dir_path]
        dir_display = dir_path if dir_path else "."
        lines.append(f"{dir_display}/")

        sorted_files = sorted(dir_info.files, key=lambda f: f.file)
        for idx, file_info in enumerate(sorted_files):
            is_last = idx == len(sorted_files) - 1
            connector = "└──" if is_last else "├──"

            fname = Path(file_info.file).name
            count = file_info.total

            if count > 0:
                torii_str = TORII * min(count, 5)
                if count > 5:
                    torii_str += "..."
                severity_parts = []
                if file_info.critical_count:
                    severity_parts.append(f"{file_info.critical_count} critical")
                if file_info.warning_count:
                    severity_parts.append(f"{file_info.warning_count} warning")
                if file_info.info_count:
                    severity_parts.append(f"{file_info.info_count} info")
                severity_str = ", ".join(severity_parts)

                line = f"  {connector} {fname:<20s} {torii_str}  {count} joint{'s' if count != 1 else ''} ({severity_str})"
            else:
                line = f"  {connector} {fname:<20s} (intact)"

            lines.append(line)

        # Add density note if directory has many joints
        total = dir_info.total
        if total >= 3:
            lines.append(f"{'':>4}↑ gold density: {dir_path} may need refactoring")

    return "\n".join(lines)


def find_hotspots(
    file_map: Dict[str, FileScarInfo],
    threshold: int = 3,
) -> List[Tuple[str, int]]:
    """Find files with scar density above the threshold.

    Returns:
        List of (file_path, joint_count) sorted by count descending.
    """
    hotspots = []
    for path, info in file_map.items():
        if info.total >= threshold:
            hotspots.append((path, info.total))
    return sorted(hotspots, key=lambda x: -x[1])
