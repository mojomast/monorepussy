"""Pipeline topology loading from YAML/JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import Hop, PipelineTopology, Route


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a simple YAML subset (no external deps).

    Supports:
    - Key: value pairs (strings, numbers, booleans)
    - Nested maps via indentation
    - Lists via - prefix (list items can be dicts with sub-keys)
    - Quoted strings
    """
    root: dict[str, Any] = {}
    # Stack: (indent_level, dict_to_write_into)
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.rstrip()
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(stripped)

        # Pop stack to find parent at this indent level
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current = stack[-1][1]

        # List item
        if stripped.startswith("- "):
            rest = stripped[2:].strip()
            colon_idx = rest.find(":")

            if colon_idx > 0:
                key = rest[:colon_idx].strip().strip('"').strip("'")
                value_part = rest[colon_idx + 1:].strip()
                new_dict: dict[str, Any] = {}
                if value_part:
                    new_dict[key] = _parse_yaml_value(value_part)
                target_list = _get_or_create_list(current)
                target_list.append(new_dict)
                stack.append((indent, new_dict))
            else:
                item_value = _parse_yaml_value(rest)
                target_list = _get_or_create_list(current)
                target_list.append(item_value)

            i += 1
            continue

        # Key: value
        colon_idx = stripped.find(":")
        if colon_idx > 0:
            key = stripped[:colon_idx].strip().strip('"').strip("'")
            value_part = stripped[colon_idx + 1:].strip()

            if value_part:
                current[key] = _parse_yaml_value(value_part)
            else:
                # Peek ahead to see if next non-empty line at higher indent
                # starts with "- " (meaning this key's value is a list)
                is_list = False
                for j in range(i + 1, len(lines)):
                    peek_line = lines[j].rstrip()
                    peek_stripped = peek_line.lstrip()
                    if not peek_stripped or peek_stripped.startswith("#"):
                        continue
                    peek_indent = len(peek_line) - len(peek_stripped)
                    if peek_indent <= indent:
                        break
                    if peek_stripped.startswith("- "):
                        is_list = True
                    break

                if is_list:
                    new_list: list[Any] = []
                    current[key] = new_list
                    # Push current dict (not the list) so sibling keys at same indent work
                    stack.append((indent, current))
                else:
                    new_dict2: dict[str, Any] = {}
                    current[key] = new_dict2
                    stack.append((indent, new_dict2))

        i += 1

    return root


def _get_or_create_list(current: dict) -> list:
    """Find the most recently set list in the current dict."""
    for key, val in reversed(list(current.items())):
        if isinstance(val, list):
            return val
    new_list: list[Any] = []
    return new_list


def _parse_yaml_value(value: str) -> Any:
    """Parse a single YAML value."""
    if not value:
        return None
    # Quoted string
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    # Boolean
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False
    # Null
    if value.lower() in ("null", "~", "none"):
        return None
    # Number
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    # Plain string
    return value


def load_topology(path: str | Path) -> PipelineTopology:
    """Load pipeline topology from a YAML or JSON file.

    Args:
        path: Path to topology definition file.

    Returns:
        PipelineTopology with all routes and hops.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Topology file not found: {path}")

    text = path.read_text(encoding="utf-8")

    if path.suffix in (".json",):
        data = json.loads(text)
    elif path.suffix in (".yaml", ".yml"):
        data = _parse_simple_yaml(text)
    else:
        # Try JSON first, then YAML
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _parse_simple_yaml(text)

    return _build_topology(data)


def _build_topology(data: dict[str, Any]) -> PipelineTopology:
    """Construct PipelineTopology from parsed data."""
    topology = PipelineTopology(
        name=data.get("name", "unnamed"),
        metadata=data.get("metadata", {}),
    )

    routes_data = data.get("routes", [])
    if isinstance(routes_data, list):
        for route_data in routes_data:
            route = _build_route(route_data)
            topology.routes.append(route)
    elif isinstance(routes_data, dict):
        for route_name, route_data in routes_data.items():
            if isinstance(route_data, dict):
                route_data.setdefault("name", route_name)
            route = _build_route(route_data)
            topology.routes.append(route)

    return topology


def _build_route(data: Any) -> Route:
    """Construct a Route from parsed data."""
    if isinstance(data, str):
        # Route as "hop1->hop2->hop3"
        hops = []
        for hop_name in re.split(r"\s*[-→>]+\s*", data):
            hop_name = hop_name.strip()
            if hop_name:
                hops.append(Hop(name=hop_name))
        return Route(name=data, hops=hops)

    if not isinstance(data, dict):
        return Route(name=str(data))

    name = data.get("name", "unnamed")
    hops = []

    hops_data = data.get("hops", [])
    if isinstance(hops_data, list):
        for hop_data in hops_data:
            hops.append(_build_hop(hop_data))

    return Route(name=name, hops=hops)


def _build_hop(data: Any) -> Hop:
    """Construct a Hop from parsed data."""
    if isinstance(data, str):
        return Hop(name=data)

    if not isinstance(data, dict):
        return Hop(name=str(data))

    return Hop(
        name=data.get("name", "unknown"),
        degradation=float(data.get("degradation", data.get("epsilon", 0.0))),
        reliability=float(data.get("reliability", 1.0)),
        details=data.get("details", ""),
        serialization_degradation=float(
            data.get("serialization_degradation", data.get("ser_degradation", 0.0))
        ),
        deserialization_degradation=float(
            data.get("deserialization_degradation", data.get("deser_degradation", 0.0))
        ),
    )


def parse_route_string(route_str: str) -> Route:
    """Parse a route string like 'order-service→payment→fraud-check→ledger'.

    Accepts arrows: ->, →, =>
    """
    hops = []
    parts = re.split(r"\s*(?:->|→|=>)\s*", route_str)
    for part in parts:
        part = part.strip()
        if part:
            hops.append(Hop(name=part))
    return Route(name=route_str, hops=hops)
