"""Command-line interface for Tarot — Probabilistic Risk Divination."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from tarot.cards import CardRegistry, DecisionCard, load_card_from_markdown
from tarot.engine import MonteCarloEngine, SpreadResult
from tarot.readings import ReadingGenerator, FullReading, format_reading
from tarot.bayesian import BayesianUpdater, OutcomeObservation
from tarot.evidence import EvidenceCollector, EvidenceItem, IncidentRecord
from tarot.community import CommunityDatabase


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tarot",
        description="Tarot — Probabilistic Risk Divination for Architecture Decisions",
    )
    subparsers = parser.add_subparsers(dest="command")

    # spread
    spread_p = subparsers.add_parser(
        "spread", help="Run a Monte Carlo simulation (tarot reading)"
    )
    spread_p.add_argument(
        "--cards", "-c",
        default="./decisions",
        help="Directory containing decision card markdown files (default: ./decisions)",
    )
    spread_p.add_argument(
        "--sims", "-s",
        type=int,
        default=10000,
        help="Number of Monte Carlo simulations (default: 10000)",
    )
    spread_p.add_argument(
        "--horizon",
        type=int,
        default=24,
        help="Planning horizon in months (default: 24)",
    )
    spread_p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    spread_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )

    # cards
    cards_p = subparsers.add_parser(
        "cards", help="List or manage decision cards"
    )
    cards_p.add_argument(
        "--cards-dir", "-c",
        default="./decisions",
        help="Directory containing decision card markdown files",
    )
    cards_sub = cards_p.add_subparsers(dest="cards_command")

    cards_list = cards_sub.add_parser("list", help="List all decision cards")
    cards_list.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed card information",
    )

    cards_show = cards_sub.add_parser("show", help="Show details for a specific card")
    cards_show.add_argument("adr_id", help="ADR ID to show (e.g., ADR-001)")

    # community
    comm_p = subparsers.add_parser(
        "community", help="Query community outcome database"
    )
    comm_p.add_argument(
        "action",
        choices=["search", "types", "stats"],
        help="Action: search <keyword>, types (list decision types), stats",
    )
    comm_p.add_argument(
        "keyword",
        nargs="?",
        default="",
        help="Search keyword (for 'search' action)",
    )

    # evidence
    evid_p = subparsers.add_parser(
        "evidence", help="Manage evidence for decisions"
    )
    evid_sub = evid_p.add_subparsers(dest="evidence_command")

    evid_incidents = evid_sub.add_parser(
        "incidents", help="Load incidents from JSON file"
    )
    evid_incidents.add_argument(
        "filepath", help="Path to incidents JSON file"
    )
    evid_incidents.add_argument(
        "--cards-dir", "-c",
        default="./decisions",
        help="Directory containing decision card markdown files",
    )

    evid_summary = evid_sub.add_parser(
        "summary", help="Show evidence summary for a decision"
    )
    evid_summary.add_argument("adr_id", help="ADR ID")
    evid_summary.add_argument(
        "--incidents",
        default=None,
        help="Path to incidents JSON file",
    )

    # version
    subparsers.add_parser("version", help="Show version")

    return parser


def _load_registry(cards_dir: str) -> CardRegistry:
    """Load a card registry from a directory."""
    registry = CardRegistry()
    registry.load_from_directory(cards_dir)
    return registry


def _cmd_spread(args) -> int:
    """Run a Monte Carlo spread."""
    registry = _load_registry(getattr(args, "cards", "./decisions"))
    if not registry.all_cards():
        print(f"No decision cards found in {args.cards}")
        print("Create .md files with YAML frontmatter (adr_id, title, outcomes, cascades, interactions)")
        return 1

    print(f"🔮 Reading {len(registry.all_cards())} decision cards...")
    engine = MonteCarloEngine(registry, seed=args.seed)
    spread = engine.run(simulations=args.sims, horizon_months=args.horizon)

    if getattr(args, "json_output", False):
        _print_json_spread(registry, spread)
    else:
        generator = ReadingGenerator(registry, spread)
        reading = generator.generate_full_reading()
        print(format_reading(reading))

        # Print summary stats
        print(f"\n📊 Simulation Summary")
        print(f"   Simulations: {spread.simulations:,}")
        print(f"   Horizon: {spread.horizon_months} months")
        print(f"   Avg risk events per sim: {spread.avg_risk_events:.2f}")
        print(f"   Cards analyzed: {len(registry.all_cards())}")

    return 0


def _print_json_spread(registry: CardRegistry, spread: SpreadResult):
    """Print spread results as JSON."""
    generator = ReadingGenerator(registry, spread)
    reading = generator.generate_full_reading()

    output = {
        "simulations": spread.simulations,
        "horizon_months": spread.horizon_months,
        "avg_risk_events": spread.avg_risk_events,
        "card_risk_probabilities": spread.card_risk_probabilities,
        "co_occurrences": {
            f"{k[0]}+{k[1]}": v for k, v in spread.co_occurrences.items()
        },
        "cascade_frequencies": spread.cascade_frequencies,
        "readings": {
            "tower": {
                "description": reading.tower.description if reading.tower else "",
                "severity": reading.tower.severity if reading.tower else "",
                "probability": reading.tower.probability if reading.tower else 0.0,
            },
            "wheel": {
                "description": reading.wheel.description if reading.wheel else "",
                "source_card": reading.wheel.source_card if reading.wheel else "",
            },
            "hermit": {
                "description": reading.hermit.description if reading.hermit else "",
                "orphaned_cards": reading.hermit.orphaned_cards if reading.hermit else [],
            },
            "star": {
                "description": reading.star.description if reading.star else "",
                "star_cards": reading.star.star_cards if reading.star else [],
            },
            "death": {
                "description": reading.death.description if reading.death else "",
                "death_cards": reading.death.death_cards if reading.death else [],
            },
        },
    }
    print(json.dumps(output, indent=2))


def _cmd_cards(args) -> int:
    """Manage decision cards."""
    cards_dir = getattr(args, "cards_dir", "./decisions")
    registry = _load_registry(cards_dir)
    cards_cmd = getattr(args, "cards_command", None)

    if cards_cmd == "show":
        adr_id = getattr(args, "adr_id", "")
        card = registry.get_card(adr_id)
        if not card:
            print(f"Card {adr_id} not found")
            return 1
        print(f"📜 {card.adr_id}: {card.title}")
        print(f"   Confidence: {card.confidence.value}")
        print(f"   Stability: {card.stability_tier}")
        print(f"   Risk probability: {card.risk_probability:.1%}")
        if card.outcomes:
            print(f"   Outcomes:")
            for o in card.outcomes:
                print(f"     - {o.name}: {o.probability:.1%}")
        if card.cascades:
            print(f"   Cascades:")
            for c in card.cascades:
                print(f"     - → {c.target_adr}: {c.description} ({c.trigger_probability:.0%})")
        if card.interactions:
            print(f"   Interactions:")
            for i in card.interactions:
                print(f"     - {i.interaction_type.value} {i.other_adr} (strength: {i.strength})")
        return 0

    # Default: list
    cards = registry.all_cards()
    if not cards:
        print(f"No decision cards found in {cards_dir}")
        return 1

    verbose = getattr(args, "verbose", False)
    for card in cards:
        risk = card.risk_probability
        if risk >= 0.6:
            emoji = "🔴"
        elif risk >= 0.3:
            emoji = "🟡"
        else:
            emoji = "🟢"
        line = f"{emoji} {card.adr_id}: {card.title} (risk: {risk:.0%}, stability: {card.stability_tier})"
        print(line)
        if verbose:
            if card.outcomes:
                for o in card.outcomes:
                    print(f"   - {o.name}: {o.probability:.1%}")

    return 0


def _cmd_community(args) -> int:
    """Query community database."""
    with CommunityDatabase() as db:
        action = getattr(args, "action", "stats")
        keyword = getattr(args, "keyword", "")

        if action == "search":
            if not keyword:
                print("Usage: tarot community search <keyword>")
                return 1
            results = db.search_outcomes(keyword)
            if not results:
                print(f"No community data found for '{keyword}'")
                return 0
            print(f"🔍 Community outcomes for '{keyword}':")
            for r in results:
                print(f"   {r['decision_type']}: {r['outcome']} "
                      f"({r['org_count']}/{r['total_orgs']} orgs = {r['probability']:.0%})")
        elif action == "types":
            types = db.get_decision_types()
            print("📋 Community decision types:")
            for t in types:
                print(f"   - {t}")
        elif action == "stats":
            print(f"🌍 Community Database Stats")
            print(f"   Decision types: {db.get_total_decision_types()}")
            print(f"   Total organizations: {db.get_total_organizations()}")
            counts = db.get_outcome_counts()
            for dt, count in sorted(counts.items()):
                print(f"   - {dt}: {count} outcomes reported")

    return 0


def _cmd_evidence(args) -> int:
    """Manage evidence."""
    evid_cmd = getattr(args, "evidence_command", None)
    collector = EvidenceCollector()

    if evid_cmd == "incidents":
        filepath = getattr(args, "filepath", "")
        collector.load_incidents_from_json(filepath)
        print(f"📥 Loaded {len(collector.incidents)} incidents from {filepath}")
        for inc in collector.incidents:
            print(f"   {inc.incident_id}: {inc.title} ({inc.severity}) "
                  f"— affects {', '.join(inc.affected_adrs) if inc.affected_adrs else 'N/A'}")
        return 0

    elif evid_cmd == "summary":
        adr_id = getattr(args, "adr_id", "")
        incidents_path = getattr(args, "incidents", None)
        if incidents_path:
            collector.load_incidents_from_json(incidents_path)
        summary = collector.evidence_summary(adr_id)
        print(f"🔍 Evidence summary for {adr_id}:")
        print(f"   Evidence items: {summary['evidence_count']}")
        print(f"   Incidents: {summary['incident_count']}")
        print(f"   Incident correlation: {summary['incident_correlation']:.3f}")
        if summary['sources']:
            print(f"   Sources: {', '.join(f'{k} ({v})' for k, v in summary['sources'].items())}")
        print(f"   Average relevance: {summary['average_relevance']:.2f}")
        return 0

    print("Usage: tarot evidence <incidents|summary> ...")
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)

    if command is None or command == "version":
        from tarot import __version__
        print(f"tarot v{__version__}")
        return 0

    handlers = {
        "spread": _cmd_spread,
        "cards": _cmd_cards,
        "community": _cmd_community,
        "evidence": _cmd_evidence,
    }

    handler = handlers.get(command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
