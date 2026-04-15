"""Zoonotic jump detection — monitor cross-domain pattern spills."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from endemic.models import Module, Pattern, ZoonoticJump


# Common architectural domains — ordered so more specific matches come first
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "infrastructure": ["infra", "config", "deploy", "cloud", "aws", "database", "db_", "cache", "queue", "migrate"],
    "testing": ["test", "spec", "fixture", "mock"],
    "data": ["pipeline", "etl", "transform", "processing", "analytics", "spark", "data"],
    "web": ["api", "web", "http", "flask", "django", "fastapi", "router", "endpoint", "controller", "view"],
    "core": ["core", "domain", "model", "entity", "business", "logic"],
    "utils": ["util", "helper", "common", "shared", "lib"],
}


def infer_domain(filepath: str) -> str:
    """Infer the architectural domain from a file path."""
    parts = Path(filepath).parts
    path_lower = str(filepath).lower()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in path_lower:
                return domain
            for part in parts:
                if part.lower() == keyword:
                    return domain

    return "unknown"


def is_pattern_appropriate_in_domain(pattern: Pattern, domain: str) -> bool:
    """Check if a pattern is appropriate in a given domain.

    Some patterns are fine in certain contexts but harmful in others.
    """
    appropriateness = {
        "bare-except": {"web": True, "data": False, "core": False, "infrastructure": True},
        "broad-except": {"web": True, "data": False, "core": False, "infrastructure": True},
        "pass-in-except": {"web": False, "data": False, "core": False, "infrastructure": False},
        "print-debugging": {"web": False, "data": False, "core": False, "testing": True},
        "no-type-hints": {"web": False, "data": False, "core": False, "testing": True},
        "todo-forever": {},  # Never great but not domain-specific
    }

    pattern_appropriateness = appropriateness.get(pattern.name, {})
    return pattern_appropriateness.get(domain, True)  # Default: appropriate


def detect_zoonotic_jumps(
    modules: list[Module],
    patterns: list[Pattern],
    tree: Optional[object] = None,
) -> list[ZoonoticJump]:
    """Detect patterns that have crossed architectural boundaries.

    A zoonotic jump occurs when a pattern spreads from one domain to another,
    especially when it's appropriate in the origin domain but not the target.
    """
    jumps = []

    # Group infected modules by domain
    domain_modules: dict[str, list[Module]] = {}
    for module in modules:
        domain = module.domain or infer_domain(module.path)
        module.domain = domain  # Cache it
        if domain not in domain_modules:
            domain_modules[domain] = []
        domain_modules[domain].append(module)

    # For each pattern, check if it appears in multiple domains
    pattern_names = set()
    for module in modules:
        pattern_names.update(module.patterns)

    for pname in pattern_names:
        # Find the pattern object
        pattern = None
        for p in patterns:
            if p.name == pname:
                pattern = p
                break

        if pattern is None:
            continue

        # Find which domains have this pattern
        pattern_domains: dict[str, list[Module]] = {}
        for domain, mods in domain_modules.items():
            for mod in mods:
                if pname in mod.patterns:
                    if domain not in pattern_domains:
                        pattern_domains[domain] = []
                    pattern_domains[domain].append(mod)

        # If pattern is in multiple domains, check for zoonotic jumps
        if len(pattern_domains) < 2:
            continue

        # Find origin domain (where pattern first appeared or is most prevalent)
        origin_domain = max(
            pattern_domains.keys(),
            key=lambda d: len(pattern_domains[d])
        )

        # Check each target domain
        for target_domain, target_modules in pattern_domains.items():
            if target_domain == origin_domain:
                continue

            is_appropriate = is_pattern_appropriate_in_domain(pattern, origin_domain)
            is_harmful = not is_pattern_appropriate_in_domain(pattern, target_domain)

            # Only flag as zoonotic jump if inappropriate in target
            if is_harmful or (is_appropriate and target_domain != origin_domain):
                risk = "HIGH" if is_harmful else "MEDIUM"

                for target_mod in target_modules:
                    origin_mod = pattern_domains[origin_domain][0]
                    recommendation = ""
                    if is_harmful:
                        recommendation = (
                            f"Replace {pname} with domain-specific pattern in "
                            f"{target_mod.path} within 2 sprints"
                        )

                    jumps.append(ZoonoticJump(
                        pattern_name=pname,
                        origin_domain=origin_domain,
                        target_domain=target_domain,
                        origin_module=origin_mod.path,
                        target_module=target_mod.path,
                        risk=risk,
                        recommendation=recommendation,
                        is_appropriate_in_origin=is_appropriate,
                    ))

    return jumps


def format_zoonotic_alert(jump: ZoonoticJump) -> str:
    """Format a zoonotic jump as an alert message."""
    lines = [
        "[ENDEMIC] ⚠️ ZOONOTIC JUMP DETECTED",
        f"  Pattern: {jump.pattern_name}",
        f"  Origin: {jump.origin_domain} ({jump.origin_module})",
        f"  Spilled to: {jump.target_domain} ({jump.target_module})",
    ]

    if jump.is_appropriate_in_origin:
        lines.append(
            f"  Context: Appropriate in {jump.origin_domain}, "
            f"but {'INAPPROPRIATE' if jump.risk == 'HIGH' else 'questionable'} "
            f"in {jump.target_domain}"
        )
    else:
        lines.append(
            f"  Context: Pattern is problematic in both domains"
        )

    if jump.risk == "HIGH":
        lines.append(f"  Risk: HIGH — this pattern can cause serious issues in {jump.target_domain}")

    if jump.recommendation:
        lines.append(f"  Recommendation: {jump.recommendation}")

    return "\n".join(lines)
