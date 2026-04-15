"""Export stemma as Graphviz DOT format and other formats."""

from __future__ import annotations

from .models import StemmaNode, StemmaTree, WitnessRole


def stemma_to_dot(stemma: StemmaTree, title: str = "Stemma") -> str:
    """Export a StemmaTree as Graphviz DOT format."""
    lines: list[str] = []
    lines.append(f'digraph "{title}" {{')
    lines.append('  rankdir=TB;')
    lines.append('  node [shape=box, style=filled];')
    lines.append('  edge [arrowhead=none];')
    lines.append("")

    # Define nodes
    for node in stemma.nodes:
        attrs: list[str] = []
        label = node.label

        if node.role == WitnessRole.ARCHETYPE:
            attrs.append('fillcolor="#FFD700"')
            attrs.append('shape=doubleoctagon')
            label = f"α\\nArchetype"
        elif node.role == WitnessRole.HYPERARCHETYPE:
            attrs.append('fillcolor="#90EE90"')
            attrs.append('shape=box')
        elif node.role == WitnessRole.TERMINAL:
            if node.label in stemma.contaminated:
                attrs.append('fillcolor="#FF6B6B"')
                attrs.append('shape=box')
                label = f"{node.label}*"
            else:
                attrs.append('fillcolor="#87CEEB"')
                attrs.append('shape=box')

        attrs.insert(0, f'label="{label}"')
        attr_str = ", ".join(attrs)
        safe_label = node.label.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")
        lines.append(f'  "{safe_label}" [{attr_str}];')

    lines.append("")

    # Define edges
    for node in stemma.nodes:
        for child in node.children:
            safe_parent = node.label.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")
            safe_child = child.label.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")

            edge_attrs = []
            if child.label in stemma.contaminated:
                edge_attrs.append('style=dashed')
                edge_attrs.append('color=red')

            attr_str = ", ".join(edge_attrs)
            if attr_str:
                lines.append(f'  "{safe_parent}" -> "{safe_child}" [{attr_str}];')
            else:
                lines.append(f'  "{safe_parent}" -> "{safe_child}";')

    # Contamination edges (dashed)
    if stemma.contaminated:
        lines.append("")
        lines.append('  // Contamination edges')
        # For contaminated witnesses, we'd need to know the contaminating source
        # This would be populated from contamination detection

    lines.append("}")
    return "\n".join(lines)


def stemma_to_text(stemma: StemmaTree) -> str:
    """Export a StemmaTree as a text tree representation."""
    if not stemma.root:
        return "(empty stemma)"

    lines: list[str] = []

    def _render(node: StemmaNode, prefix: str = "", is_last: bool = True) -> None:
        connector = "└── " if is_last else "├── "
        marker = ""
        if node.role == WitnessRole.ARCHETYPE:
            marker = " [α] Archetype"
        elif node.role == WitnessRole.HYPERARCHETYPE:
            marker = f" [{node.label}] Hyparchetype"
        elif node.label in stemma.contaminated:
            marker = f"* ⚠ Contaminated"

        if prefix == "" and node.role == WitnessRole.ARCHETYPE:
            lines.append(f"[{node.label}] — Archetype (reconstructed)")
        else:
            lines.append(f"{prefix}{connector}{node.label}{marker}")

        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            _render(child, child_prefix, i == len(node.children) - 1)

    _render(stemma.root)
    return "\n".join(lines)
