"""Pipeline topology parsing and graph construction.

Parses YAML/JSON pipeline definitions and builds the adjacency matrix
and dependency graph that represents the pipeline as an acoustic resonant cavity.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import yaml
except ImportError:  # pragma: no cover — fallback if PyYAML not installed
    yaml = None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Lock:
    """A shared lock / semaphore in the pipeline."""

    name: str
    lock_type: str  # "exclusive" or "semaphore"
    holders: list[str] = field(default_factory=list)
    capacity: int | None = None


@dataclass
class Stage:
    """A single pipeline stage (worker / processing unit)."""

    name: str
    rate: float  # items processed per second
    buffer: int  # buffer capacity
    depends_on: list[str] = field(default_factory=list)
    locks: list[str] = field(default_factory=list)


@dataclass
class PipelineTopology:
    """Full topology of a concurrent data pipeline."""

    stages: dict[str, Stage] = field(default_factory=dict)
    locks: dict[str, Lock] = field(default_factory=dict)

    # ---- derived structures (populated by build methods) ----
    _node_index: dict[str, int] = field(default_factory=dict, repr=False)
    _adjacency: np.ndarray | None = field(default=None, repr=False)

    # ---- factory methods ----

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineTopology:
        """Construct topology from a parsed dictionary."""
        stages: dict[str, Stage] = {}
        locks: dict[str, Lock] = {}

        raw_stages = data.get("stages", {})
        for name, props in raw_stages.items():
            stages[name] = Stage(
                name=name,
                rate=float(props.get("rate", 0)),
                buffer=int(props.get("buffer", 0)),
                depends_on=list(props.get("depends_on", [])),
                locks=list(props.get("locks", [])),
            )

        raw_locks = data.get("locks", {})
        for name, props in raw_locks.items():
            locks[name] = Lock(
                name=name,
                lock_type=props.get("type", "exclusive"),
                holders=list(props.get("holders", [])),
                capacity=props.get("capacity"),
            )

        topo = cls(stages=stages, locks=locks)
        topo._build_node_index()
        topo._build_adjacency()
        return topo

    @classmethod
    def from_file(cls, path: str | Path) -> PipelineTopology:
        """Load topology from a YAML or JSON file, or a directory containing pipeline.yaml."""
        p = Path(path)
        if p.is_dir():
            for candidate in ["pipeline.yaml", "pipeline.yml", "pipeline.json"]:
                candidate_path = p / candidate
                if candidate_path.exists():
                    p = candidate_path
                    break
            else:
                raise FileNotFoundError(
                    f"No pipeline.yaml or pipeline.json found in directory: {path}"
                )
        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("PyYAML is required to parse YAML files. Install it with: pip install pyyaml")
            data = yaml.safe_load(text)
        elif p.suffix == ".json":
            data = json.loads(text)
        else:
            # Try YAML first, then JSON
            if yaml is not None:
                try:
                    data = yaml.safe_load(text)
                except yaml.YAMLError:
                    data = json.loads(text)
            else:
                data = json.loads(text)
        return cls.from_dict(data)

    # ---- graph construction ----

    def _build_node_index(self) -> None:
        """Assign each stage and lock a unique integer index."""
        idx = 0
        for name in sorted(self.stages):
            self._node_index[name] = idx
            idx += 1
        for name in sorted(self.locks):
            self._node_index[name] = idx
            idx += 1

    def _build_adjacency(self) -> None:
        """Build the directed adjacency matrix for the resource dependency graph.

        Edges:
        - stage → lock   (stage *acquires* the lock)
        - lock → stage   (stage *holds/waits for* the lock)
        - stage → stage  (depends_on dependency)
        """
        n = len(self._node_index)
        if n == 0:
            self._adjacency = np.zeros((0, 0), dtype=float)
            return

        A = np.zeros((n, n), dtype=float)

        # Dependency edges: stage depends_on another stage
        for sname, stage in self.stages.items():
            si = self._node_index[sname]
            for dep in stage.depends_on:
                if dep in self._node_index:
                    di = self._node_index[dep]
                    A[si][di] = 1.0  # si depends on di

        # Acquisition edges: stage → lock (stage acquires lock)
        for sname, stage in self.stages.items():
            si = self._node_index[sname]
            for lname in stage.locks:
                if lname in self._node_index:
                    li = self._node_index[lname]
                    A[si][li] = 1.0

        # Holding edges: lock → stage (lock held by / waiting stage)
        for lname, lock in self.locks.items():
            li = self._node_index[lname]
            for holder in lock.holders:
                if holder in self._node_index:
                    hi = self._node_index[holder]
                    A[li][hi] = 1.0

        self._adjacency = A

    # ---- accessors ----

    @property
    def node_names(self) -> list[str]:
        """Return node names in index order."""
        if not self._node_index:
            return []
        names = [""] * len(self._node_index)
        for name, idx in self._node_index.items():
            names[idx] = name
        return names

    @property
    def adjacency_matrix(self) -> np.ndarray:
        """Return the adjacency matrix (rebuild if needed)."""
        if self._adjacency is None:
            self._build_node_index()
            self._build_adjacency()
        return self._adjacency

    @property
    def node_count(self) -> int:
        return len(self._node_index)

    def get_node_index(self, name: str) -> int:
        return self._node_index[name]

    def stage_impedance(self, stage_name: str) -> float:
        """Acoustic impedance Z = rate × buffer_depth for a stage."""
        stage = self.stages[stage_name]
        return stage.rate * stage.buffer

    def stage_pairs(self) -> list[tuple[str, str]]:
        """Return ordered pairs of (upstream, downstream) stages from depends_on."""
        pairs: list[tuple[str, str]] = []
        for sname, stage in self.stages.items():
            for dep in stage.depends_on:
                pairs.append((dep, sname))
        return pairs

    def lock_shared_stages(self, lock_name: str) -> list[str]:
        """Return stages that share the given lock."""
        lock = self.locks[lock_name]
        return list(lock.holders)

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a dictionary."""
        return {
            "stages": {
                name: {
                    "rate": s.rate,
                    "buffer": s.buffer,
                    "depends_on": s.depends_on,
                    "locks": s.locks,
                }
                for name, s in self.stages.items()
            },
            "locks": {
                name: {
                    "type": l.lock_type,
                    "holders": l.holders,
                    **({"capacity": l.capacity} if l.capacity is not None else {}),
                }
                for name, l in self.locks.items()
            },
        }
