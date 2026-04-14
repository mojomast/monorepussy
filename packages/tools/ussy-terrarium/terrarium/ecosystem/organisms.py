"""Organism types and visual states for the ecosystem model."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional


class OrganismType(Enum):
    """Type of organism representing a module's role."""
    TREE = "tree"           # Entry point — foundational
    BUSH = "bush"           # Library — supportive
    MOSS = "moss"           # Config — ground cover
    FLOWER = "flower"       # Test — blooms when passing
    FUNGUS = "fungus"       # Generated — grows fast, no roots
    DEAD_WOOD = "dead_wood" # Deprecated — decaying
    SEEDLING = "seedling"   # New code — small, fragile


# Mapping from module role to organism type
ROLE_TO_ORGANISM = {
    "entry_point": OrganismType.TREE,
    "library": OrganismType.BUSH,
    "config": OrganismType.MOSS,
    "test": OrganismType.FLOWER,
    "generated": OrganismType.FUNGUS,
    "deprecated": OrganismType.DEAD_WOOD,
}


class Vitality(Enum):
    """Visual vitality state of an organism."""
    THRIVING = "thriving"       # Health 80-100
    HEALTHY = "healthy"         # Health 60-79
    STRESSED = "stressed"       # Health 40-59
    WILTING = "wilting"         # Health 20-39
    DYING = "dying"             # Health 1-19
    DEAD = "dead"               # Health 0


# Emoji representations for each organism type × vitality
ORGANISM_EMOJI: Dict[OrganismType, Dict[Vitality, str]] = {
    OrganismType.TREE: {
        Vitality.THRIVING: "🌳",
        Vitality.HEALTHY: "🌲",
        Vitality.STRESSED: "🌴",
        Vitality.WILTING: "🌿",
        Vitality.DYING: "🍂",
        Vitality.DEAD: "🪵",
    },
    OrganismType.BUSH: {
        Vitality.THRIVING: "🌿",
        Vitality.HEALTHY: "🌱",
        Vitality.STRESSED: "🥀",
        Vitality.WILTING: "🌾",
        Vitality.DYING: "🍃",
        Vitality.DEAD: "💀",
    },
    OrganismType.MOSS: {
        Vitality.THRIVING: "🍀",
        Vitality.HEALTHY: "🌿",
        Vitality.STRESSED: "🌱",
        Vitality.WILTING: "🍂",
        Vitality.DYING: "🥀",
        Vitality.DEAD: "💀",
    },
    OrganismType.FLOWER: {
        Vitality.THRIVING: "🌸",
        Vitality.HEALTHY: "🌷",
        Vitality.STRESSED: "🌺",
        Vitality.WILTING: "🥀",
        Vitality.DYING: "💀",
        Vitality.DEAD: "💀",
    },
    OrganismType.FUNGUS: {
        Vitality.THRIVING: "🍄",
        Vitality.HEALTHY: "🍄",
        Vitality.STRESSED: "🦠",
        Vitality.WILTING: "🦠",
        Vitality.DYING: "💀",
        Vitality.DEAD: "💀",
    },
    OrganismType.DEAD_WOOD: {
        Vitality.THRIVING: "🪵",
        Vitality.HEALTHY: "🪵",
        Vitality.STRESSED: "🪵",
        Vitality.WILTING: "🪵",
        Vitality.DYING: "💀",
        Vitality.DEAD: "💀",
    },
    OrganismType.SEEDLING: {
        Vitality.THRIVING: "🌱",
        Vitality.HEALTHY: "🌱",
        Vitality.STRESSED: "🌱",
        Vitality.WILTING: "🌱",
        Vitality.DYING: "🥀",
        Vitality.DEAD: "💀",
    },
}

# ANSI color codes for vitality states
VITALITY_COLORS: Dict[Vitality, str] = {
    Vitality.THRIVING: "\033[32m",    # Green
    Vitality.HEALTHY: "\033[36m",     # Cyan
    Vitality.STRESSED: "\033[33m",    # Yellow
    Vitality.WILTING: "\033[35m",     # Magenta
    Vitality.DYING: "\033[31m",       # Red
    Vitality.DEAD: "\033[90m",        # Dark gray
}

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"


def health_to_vitality(health: float) -> Vitality:
    """Convert a health score (0-100) to a Vitality state."""
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


def get_emoji(organism_type: OrganismType, vitality: Vitality) -> str:
    """Get the emoji for an organism type at a given vitality."""
    return ORGANISM_EMOJI.get(organism_type, {}).get(vitality, "❓")
