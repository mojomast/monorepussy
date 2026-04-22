"""Proprioceptive drift detector — model-reality mismatch detection."""

from __future__ import annotations

import os
from pathlib import Path


def detect_drift(schema: dict, env: dict | None = None) -> list[dict]:
    """Compare persisted *schema* against ground truth and return drift events."""
    if env is None:
        env = os.environ
    drifts: list[dict] = []
    for limb in schema.get("limbs", []):
        limb_path = Path(limb["path"])
        if not limb_path.exists():
            drifts.append({
                "limb": str(limb_path),
                "type": "phantom_limb",
                "perceived": "present",
                "actual": "missing",
                "score": 1.0,
            })
            continue
        if limb["type"] == "git-repo":
            head_path = limb_path / ".git" / "HEAD"
            if head_path.exists():
                head = head_path.read_text().strip()
                stored_head = limb.get("state", {}).get("head", "")
                if head != stored_head:
                    drifts.append({
                        "limb": str(limb_path),
                        "type": "branch_drift",
                        "perceived": stored_head,
                        "actual": head,
                        "score": 0.8,
                    })
        venv = limb.get("state", {}).get("venv")
        if venv and not Path(venv).exists():
            drifts.append({
                "limb": str(limb_path),
                "type": "venv_drift",
                "perceived": venv,
                "actual": "deleted",
                "score": 0.6,
            })
    virtual_env = env.get("VIRTUAL_ENV")
    if virtual_env and not Path(virtual_env).exists():
        drifts.append({
            "limb": "shell",
            "type": "env_drift",
            "perceived": virtual_env,
            "actual": "deleted",
            "score": 0.7,
        })
    return drifts


def render_report(drifts: list[dict], threshold: float = 0.0) -> str:
    """Return a human-readable drift report."""
    lines = ["Drift Report", "=" * 40]
    filtered = [d for d in drifts if d["score"] >= threshold]
    if not filtered:
        lines.append("No drift detected. Your body schema is aligned.")
        return "\n".join(lines)
    for d in filtered:
        lines.append(
            f"[{d['type']}] {d['limb']}  score={d['score']}"
        )
        lines.append(f"    perceived: {d['perceived']}")
        lines.append(f"    actual:    {d['actual']}")
    return "\n".join(lines)
