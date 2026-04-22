"""Territory layout computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from .cochange import CochangeSummary
from .communities import TerritorySummary


@dataclass(frozen=True)
class TerritoryRegion:
    """A rendered territory polygon and grid cells."""

    territory_id: int
    name: str
    polygon: list[tuple[float, float]]
    centroid: tuple[float, float]
    color: str
    label: str


@dataclass(frozen=True)
class LayoutResult:
    """Complete layout result for rendering."""

    width: int
    height: int
    territories: list[TerritoryRegion]
    grid: list[list[int]]
    conflict_edges: set[frozenset[str]]
    edges: list[CochangeSummary]


def _point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""

    inside = False
    if not polygon:
        return False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (
            (yj - yi) or 1e-9
        ) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def _finite_voronoi_polygons(
    points: list[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    """Compute finite Voronoi polygons, with a square fallback."""

    if len(points) == 1:
        x, y = points[0]
        return [[(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)]]

    try:
        from scipy.spatial import Voronoi  # type: ignore
    except Exception:
        return [
            [(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)]
            for x, y in points
        ]

    try:
        vor = Voronoi(points)
    except Exception:
        return [
            [(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)]
            for x, y in points
        ]

    regions: list[list[tuple[float, float]]] = []
    for point_index, region_index in enumerate(vor.point_region):
        vertices = vor.regions[region_index]
        if vertices and all(v >= 0 for v in vertices):
            regions.append([tuple(vor.vertices[v]) for v in vertices])
        else:
            x, y = points[point_index]
            regions.append(
                [(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)]
            )
    if len(regions) != len(points):
        return [
            [(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)]
            for x, y in points
        ]
    return regions


def _label_from_name(name: str) -> str:
    """Short label used on the map."""

    parts = [part[:3] for part in name.replace("/", " ").split() if part]
    return "/".join(parts)[:12] or "root"


def build_layout(
    graph: nx.Graph,
    territory_summaries: list[TerritorySummary],
    width: int = 80,
    height: int = 40,
) -> LayoutResult:
    """Compute grid and polygon layout for rendering."""

    if not territory_summaries:
        return LayoutResult(
            width=width,
            height=height,
            territories=[],
            grid=[[]],
            conflict_edges=set(),
            edges=[],
        )

    community_graph = nx.Graph()
    for summary in territory_summaries:
        community_graph.add_node(summary.territory_id)
    for left, right, data in graph.edges(data=True):
        left_id = next(
            (
                summary.territory_id
                for summary in territory_summaries
                if left in summary.modules
            ),
            None,
        )
        right_id = next(
            (
                summary.territory_id
                for summary in territory_summaries
                if right in summary.modules
            ),
            None,
        )
        if left_id is None or right_id is None or left_id == right_id:
            continue
        weight = float(data.get("weight", data.get("jaccard", 0.0)))
        if community_graph.has_edge(left_id, right_id):
            community_graph[left_id][right_id]["weight"] += weight
        else:
            community_graph.add_edge(left_id, right_id, weight=weight)

    positions = nx.spring_layout(community_graph, seed=42, weight="weight")
    ordered_ids = [summary.territory_id for summary in territory_summaries]
    points = [positions.get(tid, (0.0, 0.0)) for tid in ordered_ids]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0
    scaled_points = [
        ((x - min_x) / span_x * (width - 1), (y - min_y) / span_y * (height - 1))
        for x, y in points
    ]

    polygons = _finite_voronoi_polygons(scaled_points)
    territories: list[TerritoryRegion] = []
    for summary, point, polygon in zip(territory_summaries, scaled_points, polygons):
        color = summary.label or "stable"
        territories.append(
            TerritoryRegion(
                territory_id=summary.territory_id,
                name=summary.name,
                polygon=polygon,
                centroid=point,
                color=color,
                label=_label_from_name(summary.name),
            )
        )

    grid: list[list[int]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            point = (x + 0.5, y + 0.5)
            match = None
            for region in territories:
                if _point_in_polygon(point[0], point[1], region.polygon):
                    match = region.territory_id
                    break
            if match is None:
                match = min(
                    territories,
                    key=lambda region: (
                        (region.centroid[0] - point[0]) ** 2
                        + (region.centroid[1] - point[1]) ** 2
                    ),
                ).territory_id
            row.append(match)
        grid.append(row)

    edges = []
    for left, right, data in graph.edges(data=True):
        edges.append(
            CochangeSummary(
                left,
                right,
                int(data.get("cochanges", 0)),
                float(data.get("jaccard", 0.0)),
            )
        )
    conflict_edges = {
        frozenset({edge.module_a, edge.module_b})
        for edge in edges
        if edge.jaccard > 0.3
    }

    return LayoutResult(
        width=width,
        height=height,
        territories=territories,
        grid=grid,
        conflict_edges=conflict_edges,
        edges=edges,
    )
