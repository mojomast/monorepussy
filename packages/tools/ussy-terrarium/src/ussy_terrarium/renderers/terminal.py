"""Terminal renderer — ASCII/Unicode art terrarium with ANSI colors."""

import os
from typing import Dict, List, Optional

from ..ecosystem.model import Ecosystem, Organism
from ..ecosystem.organisms import (
    OrganismType, Vitality,
    VITALITY_COLORS, ANSI_RESET, ANSI_BOLD,
    get_emoji,
)


def render_organism_line(organism: Organism, show_health: bool = True) -> str:
    """Render a single organism as a terminal line.

    Args:
        organism: The organism to render.
        show_health: Whether to show the numeric health score.

    Returns:
        A colored string like "🌳 src/main.py [85]"
    """
    color = VITALITY_COLORS.get(organism.vitality, "")
    emoji = organism.emoji

    parts = [f"{color}{emoji} {organism.path}{ANSI_RESET}"]
    if show_health:
        parts.append(f"{color}[{organism.health:.0f}]{ANSI_RESET}")

    # Add stability indicator
    stability_icons = {
        "seedling": "🌱",
        "sapling": "🌿",
        "mature": "🌳",
        "old_growth": "🏔️",
    }
    icon = stability_icons.get(organism.stability_tier, "")
    if icon:
        parts.append(icon)

    return " ".join(parts)


def render_terrarium(ecosystem: Ecosystem, width: int = 80) -> str:
    """Render the full ecosystem as a terrarium view.

    Args:
        ecosystem: The ecosystem to render.
        width: Terminal width for formatting.

    Returns:
        A string containing the full terrarium visualization.
    """
    lines = []

    # Terrarium border
    border = "═" * width
    lines.append(f"╔{border}╗")
    lines.append(f"║{ANSI_BOLD} 🌿 TERRARIUM — Codebase Ecosystem {ANSI_RESET}{' ' * (width - 38)}║")
    lines.append(f"║{'─' * width}║")

    # Overall health
    health_color = VITALITY_COLORS.get(
        _health_to_vitality(ecosystem.overall_health), ""
    )
    health_str = f"{health_color}{ecosystem.overall_health:.0f}/100 ({ecosystem.health_tier}){ANSI_RESET}"
    lines.append(f"║  Ecosystem Health: {health_str}")
    lines.append(f"║")

    # Organism counts
    count_parts = []
    if ecosystem.thriving_count:
        count_parts.append(f"{VITALITY_COLORS[Vitality.THRIVING]}{ecosystem.thriving_count} thriving{ANSI_RESET}")
    if ecosystem.healthy_count:
        count_parts.append(f"{VITALITY_COLORS[Vitality.HEALTHY]}{ecosystem.healthy_count} healthy{ANSI_RESET}")
    if ecosystem.stressed_count:
        count_parts.append(f"{VITALITY_COLORS[Vitality.STRESSED]}{ecosystem.stressed_count} stressed{ANSI_RESET}")
    if ecosystem.critical_count:
        count_parts.append(f"{VITALITY_COLORS[Vitality.WILTING]}{ecosystem.critical_count} critical{ANSI_RESET}")
    if ecosystem.dead_count:
        count_parts.append(f"{VITALITY_COLORS[Vitality.DEAD]}{ecosystem.dead_count} dead{ANSI_RESET}")

    counts_line = "  Organisms: " + ", ".join(count_parts) if count_parts else "  No organisms found"
    lines.append(f"║{counts_line}")
    lines.append(f"║{'─' * width}║")

    # Group organisms by directory
    groups = _group_by_directory(ecosystem.organisms)

    for group_name, organisms in sorted(groups.items()):
        # Group header
        group_emoji = _group_emoji(organisms)
        lines.append(f"║  {group_emoji}📁 {group_name}/")
        for organism in sorted(organisms, key=lambda o: o.health, reverse=True):
            line = render_organism_line(organism)
            lines.append(f"║    {line}")
        lines.append(f"║")

    # Most critical and healthiest
    most_critical = ecosystem.most_critical()
    healthiest = ecosystem.healthiest()

    lines.append(f"║{'─' * width}║")
    if most_critical:
        c_color = VITALITY_COLORS.get(most_critical.vitality, "")
        lines.append(
            f"║  ⚠️  Most critical: {c_color}{most_critical.path} "
            f"(health: {most_critical.health:.0f}/100){ANSI_RESET}"
        )
    if healthiest:
        h_color = VITALITY_COLORS.get(healthiest.vitality, "")
        lines.append(
            f"║  ✨ Healthiest: {h_color}{healthiest.path} "
            f"(health: {healthiest.health:.0f}/100){ANSI_RESET}"
        )

    lines.append(f"╚{border}╝")
    return "\n".join(lines)


def render_microscope(organism: Organism) -> str:
    """Render a microscope view of a single organism.

    Shows detailed internal structure including function health.

    Args:
        organism: The organism to inspect.

    Returns:
        A detailed view string.
    """
    lines = []
    color = VITALITY_COLORS.get(organism.vitality, "")

    lines.append(f"🔬 {color}{organism.emoji} {organism.path}{ANSI_RESET}")
    lines.append(f"   Type: {organism.organism_type.value}")
    lines.append(f"   Health: {organism.health:.0f}/100 ({organism.vitality.value})")
    lines.append(f"   Stability: {organism.stability_tier}")
    lines.append(f"   Age: {organism.age_tier}")
    lines.append("")

    if organism.symptoms:
        lines.append("   Symptoms:")
        for s in organism.symptoms:
            lines.append(f"     - {s}")
    else:
        lines.append("   No symptoms detected ✅")

    if organism.strengths:
        lines.append("")
        lines.append("   Strengths:")
        for s in organism.strengths:
            lines.append(f"     + {s}")

    return "\n".join(lines)


def render_health_summary(ecosystem: Ecosystem) -> str:
    """Render a compact health summary.

    Args:
        ecosystem: The ecosystem to summarize.

    Returns:
        A one-line health summary string.
    """
    health_color = VITALITY_COLORS.get(
        _health_to_vitality(ecosystem.overall_health), ""
    )
    return (
        f"Ecosystem Health: {health_color}{ecosystem.overall_health:.0f}/100 "
        f"({ecosystem.health_tier}){ANSI_RESET}\n"
        f"  {ecosystem.thriving_count} thriving, "
        f"{ecosystem.healthy_count} healthy, "
        f"{ecosystem.stressed_count} stressed, "
        f"{ecosystem.critical_count} critical, "
        f"{ecosystem.dead_count} dead"
    )


def _health_to_vitality(health: float) -> Vitality:
    """Convert health score to vitality."""
    if health >= 80:
        return Vitality.THRIVING
    elif health >= 60:
        return Vitality.HEALTHY
    elif health >= 40:
        return Vitality.STRESSED
    elif health >= 20:
        return Vitality.WILTING
    elif health > 0:
        return Vitality.DYING
    else:
        return Vitality.DEAD


def _group_by_directory(organisms: Dict[str, Organism]) -> Dict[str, List[Organism]]:
    """Group organisms by their parent directory."""
    groups: Dict[str, List[Organism]] = {}
    for path, organism in organisms.items():
        parts = path.replace("\\", "/").split("/")
        if len(parts) > 1:
            group = parts[0]
        else:
            group = "."
        groups.setdefault(group, []).append(organism)
    return groups


def _group_emoji(organisms: List[Organism]) -> str:
    """Choose an emoji for a directory group based on overall health."""
    if not organisms:
        return "📁"
    avg_health = sum(o.health for o in organisms) / len(organisms)
    if avg_health >= 80:
        return "🌳"
    elif avg_health >= 60:
        return "🌲"
    elif avg_health >= 40:
        return "🌿"
    elif avg_health >= 20:
        return "🍂"
    else:
        return "🪵"
