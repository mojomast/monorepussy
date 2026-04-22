"""Static export — SVG and text snapshots for CI reports."""

import os
from typing import Optional

from ..ecosystem.model import Ecosystem, Organism
from ..ecosystem.organisms import OrganismType, Vitality, VITALITY_COLORS, ANSI_RESET


# SVG color mapping for vitality states (no ANSI in SVG)
VITALITY_SVG_COLORS = {
    Vitality.THRIVING: "#2ecc71",
    Vitality.HEALTHY: "#3498db",
    Vitality.STRESSED: "#f39c12",
    Vitality.WILTING: "#e74c3c",
    Vitality.DYING: "#c0392b",
    Vitality.DEAD: "#7f8c8d",
}

# SVG organism shapes
ORGANISM_SVG_SHAPES = {
    OrganismType.TREE: "🌳",
    OrganismType.BUSH: "🌿",
    OrganismType.MOSS: "🍀",
    OrganismType.FLOWER: "🌸",
    OrganismType.FUNGUS: "🍄",
    OrganismType.DEAD_WOOD: "🪵",
    OrganismType.SEEDLING: "🌱",
}


def render_text_snapshot(ecosystem: Ecosystem) -> str:
    """Render a plain-text snapshot (no ANSI codes) suitable for CI logs.

    Args:
        ecosystem: The ecosystem to render.

    Returns:
        Plain text snapshot string.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("TERRARIUM — Codebase Ecosystem Snapshot")
    lines.append("=" * 60)
    lines.append(f"Ecosystem Health: {ecosystem.overall_health:.0f}/100 ({ecosystem.health_tier})")
    lines.append(
        f"  {ecosystem.thriving_count} thriving, "
        f"{ecosystem.healthy_count} healthy, "
        f"{ecosystem.stressed_count} stressed, "
        f"{ecosystem.critical_count} critical, "
        f"{ecosystem.dead_count} dead"
    )
    lines.append("")

    # Sort by health (worst first)
    sorted_organisms = sorted(ecosystem.organisms.values(), key=lambda o: o.health)

    for organism in sorted_organisms:
        emoji = organism.emoji
        lines.append(f"  {emoji} {organism.path} [{organism.health:.0f}] ({organism.vitality.value})")
        for symptom in organism.symptoms:
            lines.append(f"    - {symptom}")

    most_critical = ecosystem.most_critical()
    healthiest = ecosystem.healthiest()

    lines.append("")
    if most_critical:
        lines.append(f"Most critical: {most_critical.path} (health: {most_critical.health:.0f})")
    if healthiest:
        lines.append(f"Healthiest: {healthiest.path} (health: {healthiest.health:.0f})")

    lines.append("=" * 60)
    return "\n".join(lines)


def render_svg_snapshot(ecosystem: Ecosystem, width: int = 800) -> str:
    """Render an SVG snapshot of the ecosystem.

    Args:
        ecosystem: The ecosystem to render.
        width: SVG canvas width.

    Returns:
        SVG string.
    """
    organisms = list(ecosystem.organisms.values())
    if not organisms:
        return _empty_svg(width)

    # Layout: grid of organisms
    cols = max(1, min(4, len(organisms)))
    rows = (len(organisms) + cols - 1) // cols
    cell_w = width // cols
    cell_h = 80
    height = max(200, rows * cell_h + 100)

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')

    # Background
    svg_parts.append(f'<rect width="{width}" height="{height}" fill="#1a1a2e" rx="10"/>')

    # Title
    svg_parts.append(
        f'<text x="{width//2}" y="30" fill="white" text-anchor="middle" '
        f'font-size="18" font-weight="bold">🌿 Terrarium — Codebase Ecosystem</text>'
    )
    svg_parts.append(
        f'<text x="{width//2}" y="50" fill="white" text-anchor="middle" font-size="14">'
        f'Health: {ecosystem.overall_health:.0f}/100 ({ecosystem.health_tier})</text>'
    )

    # Organisms
    for i, organism in enumerate(organisms):
        col = i % cols
        row = i // cols
        x = col * cell_w + cell_w // 2
        y = row * cell_h + 80

        color = VITALITY_SVG_COLORS.get(organism.vitality, "#ffffff")
        emoji = ORGANISM_SVG_SHAPES.get(organism.organism_type, "📦")

        # Health bar background
        bar_w = cell_w - 20
        bar_x = x - bar_w // 2
        bar_y = y + 30
        svg_parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="6" fill="#333" rx="3"/>')
        # Health bar fill
        fill_w = max(1, int(bar_w * organism.health / 100))
        svg_parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{fill_w}" height="6" fill="{color}" rx="3"/>')

        # Emoji and label
        svg_parts.append(f'<text x="{x}" y="{y}" fill="white" text-anchor="middle" font-size="24">{emoji}</text>')
        # Truncate long names
        name = organism.path
        if len(name) > 20:
            name = "..." + name[-17:]
        svg_parts.append(
            f'<text x="{x}" y="{y + 20}" fill="{color}" text-anchor="middle" '
            f'font-size="10">{name}</text>'
        )
        svg_parts.append(
            f'<text x="{x}" y="{y + 48}" fill="#888" text-anchor="middle" '
            f'font-size="9">{organism.health:.0f}/100</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _empty_svg(width: int) -> str:
    """Generate an empty SVG when no organisms exist."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="100">'
        f'<rect width="{width}" height="100" fill="#1a1a2e" rx="10"/>'
        f'<text x="{width//2}" y="55" fill="#888" text-anchor="middle" font-size="14">'
        f'No organisms found in this ecosystem</text></svg>'
    )


def export_snapshot(ecosystem: Ecosystem, filepath: str, format: str = "text") -> None:
    """Export a snapshot to a file.

    Args:
        ecosystem: The ecosystem to export.
        filepath: Output file path.
        format: "text" or "svg".
    """
    if format == "svg":
        content = render_svg_snapshot(ecosystem)
    else:
        content = render_text_snapshot(ecosystem)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
