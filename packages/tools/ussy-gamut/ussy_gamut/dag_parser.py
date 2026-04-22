"""Pipeline DAG Parser — ingests pipeline definitions from various formats.

Supports:
- JSON pipeline definitions
- YAML pipeline definitions (using stdlib-only parser)
- Directory-based pipelines
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ussy_gamut.models import PipelineDAG, StageProfile
from ussy_gamut.profiler import dag_from_json, dag_from_dir, profile_stage


def parse_pipeline(path: str | Path) -> PipelineDAG:
    """Parse a pipeline definition from a file or directory.

    Dispatches to the appropriate parser based on path type and extension.
    """
    p = Path(path)

    if p.is_dir():
        return dag_from_dir(p)

    suffix = p.suffix.lower()
    if suffix == ".json":
        return dag_from_json(p)
    elif suffix in (".yaml", ".yml"):
        return dag_from_yaml(p)
    else:
        raise ValueError(f"Unsupported pipeline format: {suffix}")


def dag_from_yaml(path: str | Path) -> PipelineDAG:
    """Load a PipelineDAG from a simple YAML file.

    Uses a minimal stdlib-only YAML parser (no PyYAML dependency).
    Supports basic key-value pairs and nested mappings.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = _parse_simple_yaml(text)
    return _yaml_data_to_dag(data, p.stem)


def _yaml_data_to_dag(data: dict[str, Any], default_name: str) -> PipelineDAG:
    """Convert parsed YAML data to a PipelineDAG."""
    dag = PipelineDAG(name=data.get("name", default_name))

    for stage_data in data.get("stages", []):
        if isinstance(stage_data, dict):
            stage = profile_stage(
                system=stage_data.get("system", "unknown"),
                stage_name=stage_data.get("name", "unnamed"),
                schema=stage_data.get("fields", {}),
            )
            dag.add_stage(stage)

    for edge_data in data.get("edges", []):
        if isinstance(edge_data, dict):
            dag.add_edge(
                source=edge_data.get("source", ""),
                dest=edge_data.get("dest", ""),
                label=edge_data.get("label", ""),
            )

    return dag


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML parser for pipeline definitions.

    Handles:
    - Top-level key: value
    - Lists of mappings (stages, edges)
    - Nested mappings (fields)
    - Quoted and unquoted strings
    - Numbers
    """
    lines = text.splitlines()
    return _parse_yaml_lines(lines)


def _parse_yaml_lines(lines: list[str]) -> dict[str, Any]:
    """Parse YAML lines into a dict structure."""
    result: dict[str, Any] = {}
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty / comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())

        # Match top-level key
        m = re.match(r"^(\w+)\s*:\s*(.*)", stripped)
        if m:
            key = m.group(1)
            value_str = m.group(2).strip()

            if value_str:
                # Simple key: value
                result[key] = _yaml_value(value_str)
                i += 1
            else:
                # key followed by block
                i += 1
                # Collect nested content
                nested_lines: list[str] = []
                while i < len(lines):
                    next_line = lines[i]
                    next_stripped = next_line.strip()
                    if not next_stripped or next_stripped.startswith("#"):
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent:
                        break
                    nested_lines.append(next_line)
                    i += 1

                # Determine if it's a list or a mapping
                result[key] = _parse_yaml_block(nested_lines, indent + 2)
        else:
            i += 1

    return result


def _parse_yaml_block(lines: list[str], base_indent: int) -> Any:
    """Parse a YAML block (list of mappings or a mapping)."""
    if not lines:
        return []

    # Check if starts with list marker
    first_stripped = lines[0].strip()
    if first_stripped.startswith("- "):
        return _parse_yaml_list(lines)
    if first_stripped == "-":
        return _parse_yaml_list(lines)

    # Otherwise it's a mapping
    return _parse_yaml_mapping(lines)


def _parse_yaml_list(lines: list[str]) -> list[dict[str, Any]]:
    """Parse a YAML list of mappings."""
    items: list[dict[str, Any]] = []
    current_item_lines: list[str] = []
    current_indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.startswith("- ") or stripped == "-":
            if current_item_lines:
                items.append(_parse_yaml_mapping(current_item_lines))
            # Start new item: remove the "- " prefix
            if stripped.startswith("- "):
                after_dash = stripped[2:].strip()
                content_indent = indent + 2
                current_item_lines = [" " * content_indent + after_dash]
            else:
                current_item_lines = []
            current_indent = indent
        else:
            if current_item_lines or indent > current_indent:
                current_item_lines.append(line)

    if current_item_lines:
        items.append(_parse_yaml_mapping(current_item_lines))

    return items


def _parse_yaml_mapping(lines: list[str]) -> dict[str, Any]:
    """Parse YAML mapping lines into a dict."""
    result: dict[str, Any] = {}
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m = re.match(r"^(\w+)\s*:\s*(.*)", stripped)
        if m:
            key = m.group(1)
            value_str = m.group(2).strip()
            indent = len(line) - len(line.lstrip())

            if value_str:
                result[key] = _yaml_value(value_str)
                i += 1
            else:
                # Nested block
                i += 1
                nested: list[str] = []
                while i < len(lines):
                    nl = lines[i]
                    ns = nl.strip()
                    if not ns or ns.startswith("#"):
                        i += 1
                        continue
                    ni = len(nl) - len(nl.lstrip())
                    if ni <= indent:
                        break
                    nested.append(nl)
                    i += 1

                # Recursively parse nested block
                inner = _parse_yaml_block(nested, indent + 2)
                result[key] = inner
        else:
            i += 1

    return result


def _yaml_value(s: str) -> Any:
    """Parse a YAML scalar value."""
    # Remove quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]

    # Boolean
    if s.lower() in ("true", "yes", "on"):
        return True
    if s.lower() in ("false", "no", "off"):
        return False

    # Null
    if s.lower() in ("null", "~", ""):
        return None

    # Number
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass

    return s
