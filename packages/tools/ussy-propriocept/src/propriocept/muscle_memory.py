"""Muscle memory — motor program compression from shell history."""

from __future__ import annotations


_COMMAND_BLACKLIST = {
    "cd", "ls", "pwd", "clear", "exit", "history",
}


def _is_meaningful(cmd: str) -> bool:
    """Filter out trivial one-word commands."""
    parts = cmd.strip().split()
    if not parts:
        return False
    return parts[0] not in _COMMAND_BLACKLIST


def find_motor_programs(
    commands: list[str],
    min_freq: int = 5,
    max_len: int = 5,
) -> dict[tuple[str, ...], int]:
    """Detect frequently repeated contiguous command sequences."""
    freq: dict[tuple[str, ...], int] = {}
    for i in range(len(commands)):
        for l in range(2, max_len + 1):
            seq = tuple(commands[i : i + l])
            if len(seq) < l:
                break
            if not all(_is_meaningful(c) for c in seq):
                continue
            freq[seq] = freq.get(seq, 0) + 1
    return {seq: c for seq, c in freq.items() if c >= min_freq}


def format_alias(seq: tuple[str, ...], count: int) -> str:
    """Return a shell alias suggestion for a motor program."""
    name = "mp_" + "_".join(
        cmd.split()[0].replace("-", "_") for cmd in seq
    )[:40]
    body = " && ".join(seq)
    return f"# Used {count} times\nalias {name}='{body}'"


def extract_commands(history_text: str) -> list[str]:
    """Parse raw history text into a list of individual commands."""
    commands: list[str] = []
    for line in history_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # zsh extended history timestamps: `: 1234567890:0;cmd`
        if line.startswith(": ") and ";" in line:
            line = line.split(";", 1)[1]
        commands.append(line)
    return commands
