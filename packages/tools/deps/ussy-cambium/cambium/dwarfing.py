"""Dwarfing analysis — Constraint propagation and dwarfing detection."""

from __future__ import annotations

from cambium.models import DependencyNode, DwarfFactor


def compute_dwarf_factor(
    capability_with: float,
    capability_without: float,
) -> DwarfFactor:
    """Compute dwarf factor for a dependency."""
    return DwarfFactor(
        capability_with=capability_with,
        capability_without=capability_without,
    )


def analyze_dependency_chain(root: DependencyNode) -> list[dict]:
    """Analyze the dependency chain for dwarfing factors.

    Returns a list of dicts with name, capability, dwarf_ratio, is_dwarfing.
    """
    results: list[dict] = []
    _analyze_node(root, results, root.capability)
    return results


def _analyze_node(
    node: DependencyNode,
    results: list[dict],
    parent_capability: float,
) -> None:
    """Recursively analyze dependency nodes."""
    dwarf = compute_dwarf_factor(node.capability, parent_capability)

    entry = {
        "name": node.name,
        "capability": round(node.capability, 4),
        "dwarf_ratio": round(dwarf.dwarf_ratio, 4),
        "is_dwarfing": dwarf.is_dwarfing,
        "reduction_pct": round(dwarf.capability_reduction_pct, 1),
    }
    results.append(entry)

    for child in node.children:
        _analyze_node(child, results, node.capability)


def find_dwarfing_dependencies(root: DependencyNode) -> list[dict]:
    """Find all dwarfing dependencies in the chain."""
    analysis = analyze_dependency_chain(root)
    return [d for d in analysis if d["is_dwarfing"]]


def compute_chain_capability(root: DependencyNode) -> float:
    """Compute total capability throughput through the chain.

    Capability_chain = 1 / Σ_d (1/C_d)
    """
    return root.chain_capability


def format_dwarfing_report(root: DependencyNode) -> str:
    """Format a dwarfing analysis report."""
    lines: list[str] = []
    lines.append("Dwarf Factor Analysis")
    lines.append("═" * 55)

    analysis = analyze_dependency_chain(root)

    for entry in analysis:
        bar_len = int(entry["dwarf_ratio"] * 24)
        bar = "█" * bar_len + "░" * (24 - bar_len)
        warning = " ⚠️" if entry["is_dwarfing"] else ""
        lines.append(f"  {entry['name']:<20} {entry['dwarf_ratio']:.2f}  {bar}{warning}")

    chain_cap = compute_chain_capability(root)
    lines.append("")
    lines.append(f"  Chain capability throughput: {chain_cap:.2f}")

    dwarfing = [d for d in analysis if d["is_dwarfing"]]
    if dwarfing:
        lines.append("")
        lines.append("  ⚠️  DWARFING DEPENDENCIES DETECTED:")
        for d in dwarfing:
            lines.append(f"    - {d['name']}: reduces capability by {d['reduction_pct']:.0f}%")
    else:
        lines.append("  ✅ No dwarfing dependencies detected")

    return "\n".join(lines)
