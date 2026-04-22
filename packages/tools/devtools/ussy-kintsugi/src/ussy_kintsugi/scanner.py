"""Scanner module — scans source files for golden joint annotations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .joint import Joint


# Pattern to match kintsugi joint annotations in source code
JOINT_HEADER_RE = re.compile(
    r"#\s*⛩️\s*KINTSUGI JOINT:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\w+)"
)
BREAK_RE = re.compile(r"#\s*BREAK:\s*(.+)")
REPAIR_RE = re.compile(r"#\s*REPAIR:\s*(.+)")
REMOVAL_RE = re.compile(r"#\s*IF REMOVED:\s*(.+)")
STRESS_RE = re.compile(r"#\s*STRESS TEST:\s*(.+)")


@dataclass
class ScanResult:
    """Result of scanning a file for golden joints."""

    file: str = ""
    joints: List[Joint] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def parse_inline_joint(lines: List[str], start_idx: int) -> Optional[dict]:
    """Parse a golden joint annotation block starting at the given line index.

    Expected format:
        # ⛩️ KINTSUGI JOINT: 2024-03-15 | PROJ-892 | CRITICAL
        # BREAK: user.email was None ...
        # REPAIR: Added None guard ...
        # IF REMOVED: TypeError crash ...
        # STRESS TEST: test_oauth_null_email_crash (mutant: remove guard → FAIL)
    """
    data = {}

    header_match = JOINT_HEADER_RE.match(lines[start_idx])
    if not header_match:
        return None

    data["timestamp"] = header_match.group(1).strip()
    data["bug_ref"] = header_match.group(2).strip()
    data["severity"] = header_match.group(3).strip().lower()

    # Scan subsequent comment lines for additional fields
    for i in range(start_idx + 1, min(start_idx + 6, len(lines))):
        line = lines[i]

        m = BREAK_RE.match(line)
        if m:
            data["break_description"] = m.group(1).strip()
            continue

        m = REPAIR_RE.match(line)
        if m:
            data["repair_description"] = m.group(1).strip()
            continue

        m = REMOVAL_RE.match(line)
        if m:
            data["removal_impact"] = m.group(1).strip()
            continue

        m = STRESS_RE.match(line)
        if m:
            # Extract test name (before any parenthetical)
            test_ref = m.group(1).strip().split("(")[0].strip()
            data["test_ref"] = test_ref
            continue

    data["line"] = start_idx + 1  # 1-indexed
    return data


def scan_file(file_path: str) -> ScanResult:
    """Scan a single source file for golden joint annotations."""
    result = ScanResult(file=file_path)
    path = Path(file_path)

    if not path.exists():
        result.errors.append(f"File not found: {file_path}")
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        result.errors.append(f"Error reading {file_path}: {e}")
        return result

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if JOINT_HEADER_RE.match(lines[i]):
            parsed = parse_inline_joint(lines, i)
            if parsed:
                parsed["file"] = file_path
                try:
                    joint = Joint(**{k: v for k, v in parsed.items() if k in Joint.__dataclass_fields__})
                    result.joints.append(joint)
                except Exception as e:
                    result.errors.append(f"Error creating joint at line {i+1}: {e}")
            i += 5  # Skip the annotation block
        else:
            i += 1

    return result


def scan_directory(directory: str, extensions: Optional[List[str]] = None) -> List[ScanResult]:
    """Scan a directory recursively for files with golden joint annotations.

    Args:
        directory: Root directory to scan.
        extensions: File extensions to include (e.g., ['.py', '.js']). Defaults to ['.py'].
    """
    if extensions is None:
        extensions = [".py"]

    root = Path(directory)
    if not root.exists():
        return []

    results = []
    for ext in extensions:
        for path in root.rglob(f"*{ext}"):
            # Skip hidden dirs and .kintsugi dir
            parts = path.relative_to(root).parts
            if any(p.startswith(".") for p in parts):
                continue
            results.append(scan_file(str(path)))

    return results


def insert_annotation(
    file_path: str,
    line_number: int,
    bug_ref: str,
    severity: str,
    break_description: str,
    repair_description: str,
    removal_impact: str = "",
    test_ref: str = "",
    timestamp: str = "",
) -> None:
    """Insert a golden joint annotation into a source file above the given line.

    Args:
        file_path: Path to the source file.
        line_number: 1-indexed line number where the repair code is.
        bug_ref: Bug reference ID.
        severity: Severity level (critical, warning, info).
        break_description: What broke.
        repair_description: How it was repaired.
        removal_impact: What happens if the repair is removed.
        test_ref: Reference to a stress test.
        timestamp: ISO timestamp string.
    """
    from datetime import datetime, timezone

    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    severity_label = severity.upper()

    annotation_lines = [
        f"# ⛩️ KINTSUGI JOINT: {timestamp} | {bug_ref} | {severity_label}",
        f"# BREAK: {break_description}",
        f"# REPAIR: {repair_description}",
    ]
    if removal_impact:
        annotation_lines.append(f"# IF REMOVED: {removal_impact}")
    if test_ref:
        annotation_lines.append(f"# STRESS TEST: {test_ref}")

    path = Path(file_path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Insert at 0-indexed position
    insert_idx = max(0, line_number - 1)
    annotation_block = [line + "\n" for line in annotation_lines]
    lines[insert_idx:insert_idx] = annotation_block

    path.write_text("".join(lines), encoding="utf-8")
