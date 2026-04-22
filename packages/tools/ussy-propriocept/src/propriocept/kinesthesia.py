"""Kinesthesia — context velocity and flow tracking from shell history."""

from __future__ import annotations

import re
from pathlib import Path


def parse_history(path: Path = Path.home() / ".bash_history") -> list[tuple[str, str]]:
    """Read a shell history file and extract movement events."""
    moves: list[tuple[str, str]] = []
    if not path.exists():
        return moves
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        # zsh extended history timestamps: `: 1234567890:0;cmd`
        line = raw
        if line.startswith(": ") and ";" in line:
            line = line.split(";", 1)[1]
        if line.startswith("cd "):
            moves.append(("nav", line[3:].strip()))
            continue
        m = re.search(r"git\s+(checkout|switch)\s+(\S+)", line)
        if m:
            moves.append(("branch", m.group(2)))
            continue
        m = re.match(r"^(vim?|code|nano)\s+(\S+)", line)
        if m:
            moves.append(("open", m.group(2)))
            continue
    return moves


def kinesthetic_velocity(moves: list[tuple[str, str]], window: int = 50) -> float:
    """Compute the fraction of recent moves that switch context."""
    if len(moves) < 2:
        return 0.0
    recent = moves[-window:]
    switches = sum(
        1
        for i in range(1, len(recent))
        if recent[i][1] != recent[i - 1][1]
    )
    return switches / (len(recent) - 1)


def compute_vectors(moves: list[tuple[str, str]]) -> dict:
    """Return a dictionary of kinesthetic metrics."""
    velocity = kinesthetic_velocity(moves)
    # Oscillation = how often direction reverses (e.g. frontend <-> backend)
    oscillation = 0.0
    if len(moves) >= 3:
        reversals = sum(
            1
            for i in range(2, len(moves))
            if moves[i][1] == moves[i - 2][1] and moves[i][1] != moves[i - 1][1]
        )
        oscillation = reversals / (len(moves) - 2)
    return {
        "total_moves": len(moves),
        "velocity": round(velocity, 3),
        "oscillation": round(oscillation, 3),
        "flow_guard": velocity > 0.8,
    }
