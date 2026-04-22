"""SVG renderers for TimeLoom."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..color import darken, lighten
from ..weave_engine import WeaveDraft


def _cell_label(file_name: str, commit_message: str) -> str:
    return escape(f"{file_name}: {commit_message}")


def render_weave_svg(
    draft: WeaveDraft,
    file_names: list[str],
    commit_messages: list[str],
    width: int = 1200,
    thread_gap: int = 2,
    include_legend: bool = True,
) -> str:
    """Render a weave draft as an SVG textile."""

    cell_w = max(6, (width - 160) // max(1, draft.width))
    cell_h = max(8, cell_w)
    svg_width = 140 + draft.width * cell_w
    svg_height = 100 + draft.height * cell_h + (80 if include_legend else 20)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        "<title>TimeLoom weave</title>",
        '<rect width="100%" height="100%" fill="#faf7f2"/>',
    ]
    parts.append('<g transform="translate(120,40)">')
    for row_idx, row in enumerate(draft.cells):
        for col_idx, value in enumerate(row):
            x = col_idx * cell_w
            y = row_idx * cell_h
            base = draft.thread_colors[col_idx]
            row_color = draft.row_colors[row_idx]
            fill = darken(base, 0.82) if value else lighten(row_color, 1.08)
            opacity = "1" if value else "0.92"
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - thread_gap}" height="{cell_h - thread_gap}" fill="{fill}" opacity="{opacity}">'
                f"<title>{_cell_label(file_names[col_idx], commit_messages[row_idx])}</title></rect>"
            )
    for idx, file_name in enumerate(file_names):
        parts.append(
            f'<text x="{-10}" y="{idx * cell_h + cell_h * 0.7}" font-size="10" text-anchor="end" fill="#333">{escape(file_name[:32])}</text>'
        )
    parts.append("</g>")
    if include_legend:
        parts.append('<g transform="translate(120, 20)">')
        parts.append('<text x="0" y="0" font-size="12" fill="#222">Legend</text>')
        parts.append(
            '<text x="70" y="0" font-size="12" fill="#555">warp crossings</text>'
        )
        parts.append(
            '<text x="200" y="0" font-size="12" fill="#555">weft passages</text>'
        )
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


def render_heatmap_svg(
    matrix: list[list[int]], files: list[str], commits: list[str], width: int = 1200
) -> str:
    """Render a co-change heatmap as SVG."""

    cols = len(commits)
    rows = len(files)
    cell_w = max(8, (width - 160) // max(1, cols))
    cell_h = max(10, cell_w)
    svg_width = 140 + cols * cell_w
    svg_height = 80 + rows * cell_h
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">',
        "<title>TimeLoom heatmap</title>",
    ]
    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            shade = "#d1495b" if value else "#f0e6d2"
            parts.append(
                f'<rect x="{120 + col_idx * cell_w}" y="{40 + row_idx * cell_h}" width="{cell_w - 1}" height="{cell_h - 1}" fill="{shade}"><title>{escape(files[row_idx])} / {escape(commits[col_idx])}</title></rect>'
            )
    for idx, name in enumerate(commits):
        parts.append(
            f'<text x="{120 + idx * cell_w}" y="30" font-size="10" fill="#333" transform="rotate(-45 {120 + idx * cell_w} 30)">{escape(name[:20])}</text>'
        )
    for idx, name in enumerate(files):
        parts.append(
            f'<text x="10" y="{50 + idx * cell_h}" font-size="10" fill="#333">{escape(name[:24])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
