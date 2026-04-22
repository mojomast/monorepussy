"""Convert co-change matrices into weave drafts."""

from __future__ import annotations

from dataclasses import dataclass

from .color import commit_type_color, directory_color
from .git_parser import CoChangeMatrix


@dataclass(slots=True)
class WeaveDraft:
    """Standard weave draft notation."""

    width: int
    height: int
    cells: list[list[int]]
    thread_colors: list[str]
    row_colors: list[str]


def build_weave_draft(matrix: CoChangeMatrix, color_scheme: str = "warm") -> WeaveDraft:
    """Convert a co-change matrix into a weave draft."""

    thread_colors = [
        directory_color(
            path.rsplit("/", 1)[0] if "/" in path else "root", scheme=color_scheme
        )
        for path in matrix.files
    ]
    row_colors = [
        commit_type_color(commit.change_type, scheme=color_scheme)
        for commit in matrix.commits
    ]
    # Transpose: git_parser stores files×commits, but weave draft needs commits×files
    # so each row = one commit (weft pass), each column = one file (warp thread)
    num_files = len(matrix.files)
    num_commits = len(matrix.commits)
    transposed = [
        [matrix.matrix[file_idx][commit_idx] for file_idx in range(num_files)]
        for commit_idx in range(num_commits)
    ]

    return WeaveDraft(
        width=num_files,
        height=num_commits,
        cells=transposed,
        thread_colors=thread_colors,
        row_colors=row_colors,
    )


def crossing_density(draft: WeaveDraft) -> float:
    """Return the ratio of crossing cells to total cells."""

    total = draft.width * draft.height
    if not total:
        return 0.0
    ones = sum(sum(row) for row in draft.cells)
    return ones / total
