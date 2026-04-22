"""Gamut Profiler — resolves data types to formal gamut profiles.

Provides a unified interface to the system-specific profilers and can build
StageProfile objects from pipeline schema definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gamut.models import (
    FieldProfile,
    PipelineDAG,
    StageProfile,
    TypeGamut,
)
from gamut.systems import SYSTEM_PROFILERS


def get_profiler(system: str):
    """Return the profiler for a given system name, or None."""
    return SYSTEM_PROFILERS.get(system.lower())


def resolve_type(system: str, type_name: str, **kwargs: Any) -> TypeGamut:
    """Resolve a type name in a given system to a TypeGamut."""
    profiler = get_profiler(system)
    if profiler is None:
        return TypeGamut(
            system=system,
            type_name=type_name,
            field_type=__import__("gamut.models", fromlist=["FieldType"]).FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
    return profiler.resolve_type(type_name, **kwargs)


def profile_stage(system: str, stage_name: str, schema: dict[str, dict[str, Any]]) -> StageProfile:
    """Build a StageProfile from a system name and schema dict."""
    profiler = get_profiler(system)
    if profiler is None:
        raise ValueError(f"Unknown system: {system!r}. Known: {list(SYSTEM_PROFILERS.keys())}")
    return profiler.profile_stage(stage_name, schema)


def profile_from_json(path: str | Path) -> StageProfile:
    """Load a stage profile from a JSON file.

    Expected format:
    {
        "stage_name": "...",
        "system": "postgresql",
        "fields": {
            "field1": {"type": "INTEGER"},
            "field2": {"type": "TIMESTAMPTZ"}
        }
    }
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    system = data.get("system", "unknown")
    stage_name = data.get("stage_name", p.stem)
    fields = data.get("fields", {})

    return profile_stage(system, stage_name, fields)


def dag_from_json(path: str | Path) -> PipelineDAG:
    """Load a PipelineDAG from a JSON file.

    Expected format:
    {
        "name": "my_pipeline",
        "stages": [
            {
                "name": "source",
                "system": "postgresql",
                "fields": {"f1": {"type": "INTEGER"}, ...}
            },
            ...
        ],
        "edges": [
            {"source": "source", "dest": "dest", "label": "etl"},
            ...
        ]
    }
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    dag = PipelineDAG(name=data.get("name", p.stem))

    for stage_data in data.get("stages", []):
        stage = profile_stage(
            system=stage_data.get("system", "unknown"),
            stage_name=stage_data.get("name", "unnamed"),
            schema=stage_data.get("fields", {}),
        )
        dag.add_stage(stage)

    for edge_data in data.get("edges", []):
        dag.add_edge(
            source=edge_data.get("source", ""),
            dest=edge_data.get("dest", ""),
            label=edge_data.get("label", ""),
        )

    return dag


def dag_from_dir(path: str | Path) -> PipelineDAG:
    """Load a PipelineDAG from a directory of JSON stage files.

    Each .json file in the directory is a stage profile. Edges are inferred
    from a _pipeline.json file if present, or from alphabetical ordering.
    """
    p = Path(path)
    if not p.is_dir():
        raise ValueError(f"Not a directory: {path}")

    dag = PipelineDAG(name=p.name)
    stage_files = sorted(p.glob("*.json"))

    pipeline_file = p / "_pipeline.json"
    edges_data: list[dict[str, str]] = []

    if pipeline_file.exists():
        with pipeline_file.open("r", encoding="utf-8") as f:
            pdata = json.load(f)
        dag.name = pdata.get("name", dag.name)
        edges_data = pdata.get("edges", [])

    for sf in stage_files:
        if sf.name == "_pipeline.json":
            continue
        stage = profile_from_json(sf)
        dag.add_stage(stage)

    # Add edges from pipeline file
    if edges_data:
        for ed in edges_data:
            dag.add_edge(
                source=ed.get("source", ""),
                dest=ed.get("dest", ""),
                label=ed.get("label", ""),
            )
    else:
        # Infer edges from alphabetical order
        names = list(dag.stages.keys())
        for i in range(len(names) - 1):
            dag.add_edge(source=names[i], dest=names[i + 1])

    return dag
