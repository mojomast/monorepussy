"""Superspreader identification — find modules and developers that disproportionately propagate patterns."""

from __future__ import annotations

from typing import Optional

from endemic.models import (
    DeveloperStats,
    Module,
    TransmissionEvent,
    TransmissionTree,
)


def identify_superspreader_modules(
    tree: TransmissionTree,
    top_n: int = 5,
) -> list[tuple[str, int]]:
    """Identify modules that are superspreaders.

    Returns list of (module_path, secondary_infections) sorted by infection count.
    A superspreader is any module that caused more than the mean number of
    secondary infections + 1 standard deviation.
    """
    if not tree.events:
        return []

    # Count secondary infections per source module
    source_counts: dict[str, int] = {}
    for event in tree.events:
        source_counts[event.source_module] = source_counts.get(event.source_module, 0) + 1

    # Include index case
    if tree.index_case:
        index_infections = sum(
            1 for e in tree.events if e.source_module == tree.index_case
        )
        if index_infections > 0:
            source_counts[tree.index_case] = source_counts.get(tree.index_case, 0) + index_infections - source_counts.get(tree.index_case, 0)

    # Sort by count descending
    sorted_modules = sorted(source_counts.items(), key=lambda x: -x[1])

    # Determine threshold: mean + 1 std
    if sorted_modules:
        counts = [c for _, c in sorted_modules]
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts) if counts else 0
        std = variance ** 0.5
        threshold = mean + std

        # Return those above threshold, or top_n if none qualify
        superspreaders = [(m, c) for m, c in sorted_modules if c >= threshold]
        if not superspreaders:
            superspreaders = sorted_modules[:top_n]
        return superspreaders[:top_n]

    return []


def identify_superspreader_developers(
    tree: TransmissionTree,
    top_n: int = 5,
) -> list[DeveloperStats]:
    """Identify developers that are superspreaders.

    Returns list of DeveloperStats sorted by infections caused.
    """
    if not tree.events:
        return []

    dev_stats: dict[str, DeveloperStats] = {}
    for event in tree.events:
        email = event.developer
        if email not in dev_stats:
            dev_stats[email] = DeveloperStats(email=email)
        dev = dev_stats[email]
        dev.infections_caused += 1
        if event.target_module not in dev.modules_infected:
            dev.modules_infected.append(event.target_module)
        if event.pattern_name not in dev.patterns_introduced:
            dev.patterns_introduced.append(event.pattern_name)

    # Calculate superspreader threshold
    all_counts = [d.infections_caused for d in dev_stats.values()]
    if not all_counts:
        return []

    mean = sum(all_counts) / len(all_counts)
    variance = sum((c - mean) ** 2 for c in all_counts) / len(all_counts)
    std = variance ** 0.5
    threshold = mean + std

    # Mark superspreaders
    for dev in dev_stats.values():
        dev.is_superspreader = dev.infections_caused >= threshold

    # Sort by infections caused
    sorted_devs = sorted(dev_stats.values(), key=lambda d: -d.infections_caused)
    return sorted_devs[:top_n]


def identify_superspreader_events(
    tree: TransmissionTree,
    top_n: int = 5,
) -> list[tuple[TransmissionEvent, int]]:
    """Identify PR/commit events that caused the most infections.

    Returns list of (event, secondary_infections) sorted by impact.
    """
    if not tree.events:
        return []

    # Group by commit hash
    commit_infections: dict[str, list[TransmissionEvent]] = {}
    for event in tree.events:
        key = event.commit_hash or f"unknown-{event.target_module}"
        if key not in commit_infections:
            commit_infections[key] = []
        commit_infections[key].append(event)

    # Sort by number of infections per commit
    sorted_commits = sorted(
        commit_infections.items(), key=lambda x: -len(x[1])
    )

    result = []
    for commit_hash, events in sorted_commits[:top_n]:
        if events:
            result.append((events[0], len(events)))

    return result


def compute_superspreader_impact(
    module_path: str,
    tree: TransmissionTree,
) -> dict:
    """Compute the impact of a superspreader module.

    Returns dict with:
        direct_infections: Number of modules directly infected
        total_reach: Total modules reachable via transmission chain
        equivalent_random_vaccinations: How many random refactors this equals
    """
    direct = 0
    reachable = set()

    for event in tree.events:
        if event.source_module == module_path:
            direct += 1
            reachable.add(event.target_module)

    # BFS to find all reachable modules
    to_visit = list(reachable)
    while to_visit:
        current = to_visit.pop(0)
        for event in tree.events:
            if event.source_module == current and event.target_module not in reachable:
                reachable.add(event.target_module)
                to_visit.append(event.target_module)

    return {
        "direct_infections": direct,
        "total_reach": len(reachable),
        "equivalent_random_vaccinations": max(1, direct // 2),
    }
