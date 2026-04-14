"""Test coverage ingestion — parse coverage reports."""

import json
import os
from typing import Dict, Optional, Tuple


def parse_coverage_json(filepath: str) -> Dict[str, float]:
    """Parse a coverage.py JSON report.

    Args:
        filepath: Path to coverage.json file.

    Returns:
        Dict mapping source file path -> coverage percentage (0.0-1.0).
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    files = data.get("files", {})
    result = {}

    for path, info in files.items():
        summary = info.get("summary", {})
        covered = summary.get("covered_lines", 0)
        total = summary.get("num_statements", 0)
        if total > 0:
            result[path] = covered / total
        else:
            result[path] = 1.0

    return result


def parse_coverage_lcov(filepath: str) -> Dict[str, float]:
    """Parse a simple lcov/info coverage file.

    Args:
        filepath: Path to lcov .info file.

    Returns:
        Dict mapping source file path -> coverage percentage (0.0-1.0).
    """
    result = {}
    current_file = None
    hit_lines = 0
    total_lines = 0

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SF:"):
                    # Save previous file
                    if current_file and total_lines > 0:
                        result[current_file] = hit_lines / total_lines
                    current_file = line[3:]
                    hit_lines = 0
                    total_lines = 0
                elif line.startswith("DA:"):
                    # DA:line_number,hit_count
                    parts = line[3:].split(",")
                    if len(parts) >= 2:
                        total_lines += 1
                        try:
                            if int(parts[1]) > 0:
                                hit_lines += 1
                        except ValueError:
                            pass
                elif line == "end_of_record":
                    if current_file and total_lines > 0:
                        result[current_file] = hit_lines / total_lines
                    current_file = None
                    hit_lines = 0
                    total_lines = 0
    except OSError:
        return {}

    return result


def auto_detect_coverage(root_path: str) -> Dict[str, float]:
    """Auto-detect and parse coverage reports in a project.

    Searches for common coverage report file names.

    Returns:
        Dict mapping source file path -> coverage percentage (0.0-1.0).
    """
    candidates = [
        ("coverage.json", parse_coverage_json),
        (".coverage.json", parse_coverage_json),
    ]

    for filename, parser in candidates:
        filepath = os.path.join(root_path, filename)
        if os.path.isfile(filepath):
            result = parser(filepath)
            if result:
                return result

    # Check for lcov files
    for filename in os.listdir(root_path):
        if filename.endswith(".info") or filename.endswith(".lcov"):
            filepath = os.path.join(root_path, filename)
            result = parse_coverage_lcov(filepath)
            if result:
                return result

    return {}
