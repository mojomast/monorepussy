"""Body schema builder — maps workspace topology."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def scan_limb(path: Path) -> dict:
    """Inspect a single directory and return its limb descriptor."""
    limb: dict = {"path": str(path), "type": "bare-directory", "state": {}}
    git_dir = path / ".git"
    if git_dir.is_dir():
        limb["type"] = "git-repo"
        head = (git_dir / "HEAD").read_text().strip()
        limb["state"]["head"] = head
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        limb["state"]["dirty"] = bool(result.stdout.strip())
    for venv_name in ("venv", ".venv", "env"):
        if (path / venv_name).is_dir():
            limb["state"]["venv"] = str(path / venv_name)
            break
    return limb


def build_schema(root: Path, output: Path | None = None) -> dict:
    """Scan *root* and persist a body-schema JSON."""
    schema: dict = {"limbs": [], "root": str(root)}
    if root.is_dir():
        for child in root.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                schema["limbs"].append(scan_limb(child))
    if output is not None:
        output.write_text(json.dumps(schema, indent=2))
    return schema


def load_schema(path: Path) -> dict:
    """Load a previously persisted body schema."""
    return json.loads(path.read_text())
