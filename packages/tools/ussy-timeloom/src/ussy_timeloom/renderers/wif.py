"""WIF export for TimeLoom."""

from __future__ import annotations

from ..weave_engine import WeaveDraft


def render_wif(
    draft: WeaveDraft, file_names: list[str], commit_types: list[str]
) -> str:
    """Render a minimal WIF-like text export."""

    lines = ["[WIF]", f"Warp={draft.width}", f"Weft={draft.height}", "[Threads]"]
    for idx, (name, color) in enumerate(
        zip(file_names, draft.thread_colors, strict=False), start=1
    ):
        lines.append(f"{idx}\t{name}\t{color}")
    lines.append("[Rows]")
    for idx, (ctype, color) in enumerate(
        zip(commit_types, draft.row_colors, strict=False), start=1
    ):
        lines.append(f"{idx}\t{ctype}\t{color}")
    lines.append("[Pattern]")
    for row in draft.cells:
        lines.append(" ".join(str(cell) for cell in row))
    return "\n".join(lines)
