"""Structural analysis for weave drafts."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Any

from .weave_engine import WeaveDraft


@dataclass(slots=True)
class FloatInfo:
    file: str
    start_row: int
    end_row: int
    length: int


@dataclass(slots=True)
class PatternRepeat:
    file: str
    period: int
    score: float


@dataclass(slots=True)
class CouplingCluster:
    files: list[str]
    similarity: float


@dataclass(slots=True)
class AnalysisResult:
    float_threads: list[FloatInfo]
    selvedge_integrity: float
    pattern_repeats: list[PatternRepeat]
    coupling_clusters: list[CouplingCluster]
    total_crossings: int
    density: float


def detect_floats(
    draft: WeaveDraft, file_names: list[str], min_float_length: int = 10
) -> list[FloatInfo]:
    """Detect long runs of 0s in each file column."""

    floats: list[FloatInfo] = []
    for col_idx, file_name in enumerate(file_names):
        run_start: int | None = None
        for row_idx, row in enumerate(draft.cells):
            if row[col_idx] == 0:
                run_start = row_idx if run_start is None else run_start
            else:
                if run_start is not None and row_idx - run_start >= min_float_length:
                    floats.append(
                        FloatInfo(
                            file=file_name,
                            start_row=run_start,
                            end_row=row_idx - 1,
                            length=row_idx - run_start,
                        )
                    )
                run_start = None
        if run_start is not None and len(draft.cells) - run_start >= min_float_length:
            floats.append(
                FloatInfo(
                    file=file_name,
                    start_row=run_start,
                    end_row=len(draft.cells) - 1,
                    length=len(draft.cells) - run_start,
                )
            )
    return floats


def check_selvedge_integrity(draft: WeaveDraft, edge_width: int = 1) -> float:
    """Estimate how stable the outer edge threads are."""

    if draft.width < 2 or draft.height == 0:
        return 0.0
    width = min(edge_width, draft.width // 2)
    comparisons = 0
    matches = 0
    for row in draft.cells:
        for i in range(width):
            comparisons += 2
            matches += int(row[i] == row[i + 1])
            matches += int(row[-1 - i] == row[-2 - i])
    return matches / comparisons if comparisons else 0.0


def _best_repeat_for_column(
    column: list[int], file_name: str, max_period: int | None = None
) -> PatternRepeat | None:
    limit = max_period or max(2, len(column) // 2)
    best: PatternRepeat | None = None
    for period in range(2, limit + 1):
        left = column[:-period]
        right = column[period:]
        if not left or not right:
            continue
        score = sum(int(a == b) for a, b in zip(left, right)) / len(left)
        if best is None or score > best.score:
            best = PatternRepeat(file=file_name, period=period, score=score)
    if best and best.score >= 0.75:
        return best
    return None


def find_pattern_repeats(
    draft: WeaveDraft, file_names: list[str]
) -> list[PatternRepeat]:
    """Find repeated patterns using a simple autocorrelation score."""

    repeats: list[PatternRepeat] = []
    if draft.height < 3:
        return repeats
    for col_idx, file_name in enumerate(file_names):
        column = [row[col_idx] for row in draft.cells]
        repeat = _best_repeat_for_column(column, file_name)
        if repeat is not None:
            repeats.append(repeat)
    return repeats


def _jaccard(left: set[int], right: set[int]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def find_coupling_clusters(
    draft: WeaveDraft, file_names: list[str], threshold: float = 0.5
) -> list[CouplingCluster]:
    """Group files that co-change together frequently."""

    if draft.width < 2:
        return []
    change_sets = [
        {idx for idx, row in enumerate(draft.cells) if row[col_idx]}
        for col_idx in range(draft.width)
    ]
    parent = list(range(draft.width))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    similarities: dict[tuple[int, int], float] = {}
    for i, j in combinations(range(draft.width), 2):
        similarity = _jaccard(change_sets[i], change_sets[j])
        similarities[(i, j)] = similarity
        if similarity > threshold:
            union(i, j)

    clusters: dict[int, list[int]] = {}
    for idx in range(draft.width):
        clusters.setdefault(find(idx), []).append(idx)

    result: list[CouplingCluster] = []
    for indices in clusters.values():
        if len(indices) < 2:
            continue
        pair_scores = [
            similarities.get((min(i, j), max(i, j)), 1.0)
            for i, j in combinations(indices, 2)
        ]
        result.append(
            CouplingCluster(
                files=[file_names[i] for i in indices],
                similarity=sum(pair_scores) / len(pair_scores) if pair_scores else 1.0,
            )
        )
    return result


def analyze_draft(
    draft: WeaveDraft, file_names: list[str], min_float_length: int = 10
) -> AnalysisResult:
    """Run all structural analysis passes."""

    total_crossings = sum(sum(row) for row in draft.cells)
    total_cells = draft.width * draft.height
    return AnalysisResult(
        float_threads=detect_floats(
            draft, file_names, min_float_length=min_float_length
        ),
        selvedge_integrity=check_selvedge_integrity(draft),
        pattern_repeats=find_pattern_repeats(draft, file_names),
        coupling_clusters=find_coupling_clusters(draft, file_names),
        total_crossings=total_crossings,
        density=(total_crossings / total_cells) if total_cells else 0.0,
    )


def analysis_to_dict(result: AnalysisResult) -> dict[str, Any]:
    """Convert an analysis result into plain data."""

    return asdict(result)
