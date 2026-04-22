"""Decision Card model and Registry.

Every ADR becomes a Decision Card with probability distributions,
cascade rules, and interaction rules.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


class InteractionType(Enum):
    AMPLIFY = "AMPLIFY"
    MITIGATE = "MITIGATE"


class Confidence(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class Outcome:
    """A single possible outcome with its probability."""
    name: str
    probability: float  # 0.0 to 1.0

    def __post_init__(self):
        self.probability = max(0.0, min(1.0, self.probability))


@dataclass
class CascadeRule:
    """When this card triggers an outcome, it cascades to another decision."""
    target_adr: str
    description: str
    trigger_probability: float  # probability this cascade fires if source outcome triggers

    def __post_init__(self):
        self.trigger_probability = max(0.0, min(1.0, self.trigger_probability))


@dataclass
class InteractionRule:
    """How this card interacts with another card."""
    other_adr: str
    interaction_type: InteractionType
    strength: float = 1.0  # multiplier: >1 amplifies, <1 mitigates

    def __post_init__(self):
        self.strength = max(0.0, min(3.0, self.strength))


@dataclass
class DecisionCard:
    """A single architecture decision card with probability distributions."""
    adr_id: str
    title: str
    outcomes: List[Outcome] = field(default_factory=list)
    cascades: List[CascadeRule] = field(default_factory=list)
    interactions: List[InteractionRule] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = ""
    tags: List[str] = field(default_factory=list)
    stability_tier: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.stability_tier:
            self.stability_tier = self._compute_stability_tier()
        # Normalize outcome probabilities
        self._normalize_outcomes()

    def _compute_stability_tier(self) -> str:
        """Compute stability tier from the highest-risk outcome probability."""
        if not self.outcomes:
            return "unknown"
        max_risk = max(
            (o.probability for o in self.outcomes if o.name.lower() != "no issues"),
            default=0.0,
        )
        if max_risk >= 0.7:
            return "critical"
        elif max_risk >= 0.4:
            return "unstable"
        elif max_risk >= 0.2:
            return "moderate"
        else:
            return "stable"

    def _normalize_outcomes(self):
        """Normalize outcome probabilities so they sum to 1.0."""
        if not self.outcomes:
            return
        total = sum(o.probability for o in self.outcomes)
        if total > 0:
            for o in self.outcomes:
                o.probability = o.probability / total

    @property
    def risk_probability(self) -> float:
        """Total probability of negative outcomes."""
        return sum(
            o.probability for o in self.outcomes
            if o.name.lower() != "no issues"
        )

    def sample_outcome(self, rng) -> Optional[Outcome]:
        """Sample an outcome from the probability distribution."""
        if not self.outcomes:
            return None
        r = rng.random()
        cumulative = 0.0
        for outcome in self.outcomes:
            cumulative += outcome.probability
            if r <= cumulative:
                return outcome
        return self.outcomes[-1]


# --- Minimal YAML frontmatter parser ---

def _parse_simple_yaml(text: str) -> dict:
    """Parse a minimal subset of YAML (key: value, lists) for frontmatter."""
    result: dict = {}
    current_key = None
    current_list: list = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # List item
        if stripped.startswith("- "):
            if current_key is not None:
                val = stripped[2:].strip().strip('"').strip("'")
                current_list.append(val)
            continue
        # Key: value
        m = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', stripped)
        if m:
            # Flush previous list
            if current_key is not None and current_list:
                result[current_key] = current_list
                current_list = []
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            if val:
                result[key] = val
            else:
                current_key = key
                current_list = []
            continue
        # Continuation
        if current_key is not None:
            val = stripped.strip('"').strip("'")
            if val:
                current_list.append(val)

    if current_key is not None and current_list:
        result[current_key] = current_list

    return result


def parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = _parse_simple_yaml(parts[1])
    body = parts[2].strip()
    return meta, body


def _parse_outcomes(raw: List[str]) -> List[Outcome]:
    """Parse outcome strings like 'Schema rigidity:35%' into Outcome objects."""
    outcomes = []
    for item in raw:
        # Format: "name:probability%"
        parts = item.rsplit(":", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            try:
                prob = float(parts[1].strip().rstrip("%")) / 100.0
            except ValueError:
                prob = 0.1
            outcomes.append(Outcome(name=name, probability=prob))
        else:
            outcomes.append(Outcome(name=item.strip(), probability=0.1))
    return outcomes


def _parse_cascades(raw: List[str]) -> List[CascadeRule]:
    """Parse cascade strings like 'ADR-014:Redis cluster needed:60%'."""
    cascades = []
    for item in raw:
        parts = item.split(":")
        if len(parts) >= 3:
            target = parts[0].strip()
            desc = parts[1].strip()
            try:
                prob = float(parts[2].strip().rstrip("%")) / 100.0
            except ValueError:
                prob = 0.5
            cascades.append(CascadeRule(
                target_adr=target,
                description=desc,
                trigger_probability=prob,
            ))
        elif len(parts) == 2:
            cascades.append(CascadeRule(
                target_adr=parts[0].strip(),
                description=parts[1].strip(),
                trigger_probability=0.5,
            ))
    return cascades


def _parse_interactions(raw: List[str]) -> List[InteractionRule]:
    """Parse interaction strings like 'ADR-012:AMPLIFY:1.5'."""
    interactions = []
    for item in raw:
        parts = item.split(":")
        if len(parts) >= 2:
            other = parts[0].strip()
            itype_str = parts[1].strip().upper()
            strength = 1.5
            if len(parts) >= 3:
                try:
                    strength = float(parts[2].strip())
                except ValueError:
                    strength = 1.5
            try:
                itype = InteractionType(itype_str)
            except ValueError:
                itype = InteractionType.AMPLIFY
            interactions.append(InteractionRule(
                other_adr=other,
                interaction_type=itype,
                strength=strength,
            ))
    return interactions


def load_card_from_markdown(filepath: str) -> DecisionCard:
    """Load a DecisionCard from a markdown file with YAML frontmatter."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    meta, body = parse_frontmatter(text)

    adr_id = meta.get("adr_id", "")
    title = meta.get("title", "")

    outcomes = _parse_outcomes(meta.get("outcomes", []))
    cascades = _parse_cascades(meta.get("cascades", []))
    interactions = _parse_interactions(meta.get("interactions", []))

    conf_str = meta.get("confidence", "Medium")
    try:
        confidence = Confidence(conf_str)
    except ValueError:
        confidence = Confidence.MEDIUM

    evidence = meta.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]

    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    created_at = meta.get("created_at", "")

    return DecisionCard(
        adr_id=adr_id,
        title=title,
        outcomes=outcomes,
        cascades=cascades,
        interactions=interactions,
        confidence=confidence,
        evidence_refs=evidence,
        created_at=created_at,
        tags=tags,
    )


class CardRegistry:
    """Registry of all decision cards, loadable from a directory."""

    def __init__(self):
        self.cards: Dict[str, DecisionCard] = {}

    def add_card(self, card: DecisionCard):
        self.cards[card.adr_id] = card

    def remove_card(self, adr_id: str):
        self.cards.pop(adr_id, None)

    def get_card(self, adr_id: str) -> Optional[DecisionCard]:
        return self.cards.get(adr_id)

    def all_cards(self) -> List[DecisionCard]:
        return list(self.cards.values())

    def load_from_directory(self, directory: str):
        """Load all .md files from a directory as decision cards."""
        if not os.path.isdir(directory):
            return
        for fname in sorted(os.listdir(directory)):
            if fname.endswith(".md"):
                filepath = os.path.join(directory, fname)
                try:
                    card = load_card_from_markdown(filepath)
                    if card.adr_id:
                        self.add_card(card)
                except Exception:
                    # Skip malformed files
                    pass

    def save_card_to_markdown(self, card: DecisionCard, directory: str) -> str:
        """Save a DecisionCard as a markdown file with YAML frontmatter."""
        os.makedirs(directory, exist_ok=True)
        filename = f"{card.adr_id.lower().replace(' ', '-')}.md"
        filepath = os.path.join(directory, filename)

        lines = ["---"]
        lines.append(f"adr_id: {card.adr_id}")
        lines.append(f"title: {card.title}")
        lines.append(f"confidence: {card.confidence.value}")
        lines.append(f"created_at: {card.created_at}")

        if card.outcomes:
            lines.append("outcomes:")
            for o in card.outcomes:
                pct = round(o.probability * 100, 1)
                lines.append(f"  - \"{o.name}:{pct}%\"")

        if card.cascades:
            lines.append("cascades:")
            for c in card.cascades:
                pct = round(c.trigger_probability * 100, 1)
                lines.append(f"  - \"{c.target_adr}:{c.description}:{pct}%\"")

        if card.interactions:
            lines.append("interactions:")
            for i in card.interactions:
                lines.append(f"  - \"{i.other_adr}:{i.interaction_type.value}:{i.strength}\"")

        if card.evidence_refs:
            lines.append("evidence:")
            for e in card.evidence_refs:
                lines.append(f"  - \"{e}\"")

        if card.tags:
            lines.append("tags:")
            for t in card.tags:
                lines.append(f"  - \"{t}\"")

        lines.append("---")
        lines.append("")
        lines.append(f"# {card.adr_id}: {card.title}")
        lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def get_interacting_cards(self, adr_id: str) -> List[Tuple[DecisionCard, InteractionRule]]:
        """Get all cards that interact with the given card."""
        card = self.get_card(adr_id)
        if not card:
            return []
        result = []
        for interaction in card.interactions:
            other = self.get_card(interaction.other_adr)
            if other:
                result.append((other, interaction))
        return result

    def get_cascade_targets(self, adr_id: str) -> List[Tuple[DecisionCard, CascadeRule]]:
        """Get all cards that are cascade targets of the given card."""
        card = self.get_card(adr_id)
        if not card:
            return []
        result = []
        for cascade in card.cascades:
            target = self.get_card(cascade.target_adr)
            if target:
                result.append((target, cascade))
        return result

    def get_orphaned_cards(self) -> List[DecisionCard]:
        """Get cards with no mitigations and no one mitigating them."""
        mitigated_by_someone = set()
        for card in self.cards.values():
            for interaction in card.interactions:
                if interaction.interaction_type == InteractionType.MITIGATE:
                    mitigated_by_someone.add(interaction.other_adr)

        orphans = []
        for card in self.cards.values():
            has_mitigation = any(
                i.interaction_type == InteractionType.MITIGATE
                for i in card.interactions
            )
            is_mitigated_by_others = card.adr_id in mitigated_by_someone
            if not has_mitigation and not is_mitigated_by_others and card.risk_probability > 0:
                orphans.append(card)
        return orphans

    def get_mitigators(self) -> List[Tuple[DecisionCard, int]]:
        """Get cards that mitigate other risks, sorted by impact."""
        mitigators: Dict[str, int] = {}
        for card in self.cards.values():
            for interaction in card.interactions:
                if interaction.interaction_type == InteractionType.MITIGATE:
                    mitigators[card.adr_id] = mitigators.get(card.adr_id, 0) + 1

        result = [(self.cards[aid], count) for aid, count in mitigators.items() if aid in self.cards]
        result.sort(key=lambda x: x[1], reverse=True)
        return result
