"""Display formatting for Stemma output."""

from __future__ import annotations

from .models import (
    ArchetypeResult,
    Classification,
    CollationResult,
    ContaminationReport,
    StemmaTree,
    VariantType,
)


CLASSIFICATION_ICONS = {
    Classification.SCRIBAL_ERROR: "🐛",
    Classification.CONSCIOUS_MODIFICATION: "✏️",
    Classification.AMBIGUOUS: "🤔",
}

CLASSIFICATION_LABELS = {
    Classification.SCRIBAL_ERROR: "SCRIBAL ERROR",
    Classification.CONSCIOUS_MODIFICATION: "CONSCIOUS MODIFICATION",
    Classification.AMBIGUOUS: "AMBIGUOUS",
}


def format_collation(collation: CollationResult) -> str:
    """Format collation result as a readable table."""
    lines: list[str] = []

    # Header
    wit_labels = [w.label for w in collation.witnesses]
    wit_sources = [w.source for w in collation.witnesses]

    # Determine function name from first witness source
    func_name = wit_sources[0] if wit_sources else "unknown"

    lines.append(f"COLLATION: {func_name} — {len(collation.witnesses)} witnesses")
    lines.append("")

    # Variation units
    for unit in collation.variation_units:
        if not unit.is_variant:
            # Unanimous line
            if unit.readings:
                lines.append(
                    f"  L{unit.line_number:3d}  {unit.readings[0].text:<30s}  "
                    f"{' '.join(unit.readings[0].witnesses)} (unanimous)"
                )
        else:
            # Variant line
            for i, reading in enumerate(unit.readings):
                vtype = reading.variant_type.value
                prefix = f"  L{unit.line_number:3d}" if i == 0 else f"      "
                lines.append(
                    f"{prefix}  {reading.text:<30s}  "
                    f"{' '.join(reading.witnesses)} ({vtype})"
                )

    # Footer
    lines.append("")
    wit_desc = ", ".join(
        f"{w.label}={w.source}" for w in collation.witnesses
    )
    lines.append(f"  Witnesses: {wit_desc}")
    lines.append(
        f"  Variants: {collation.variant_count} variation units "
        f"across {collation.total_lines} lines"
    )
    lines.append(
        f"  Shared readings: {collation.unanimous_count}/{collation.total_lines} lines unanimous"
    )

    return "\n".join(lines)


def format_stemma(stemma: StemmaTree) -> str:
    """Format stemma tree as readable output."""
    from .export import ussy_stemma_to_text
    lines: list[str] = []

    lines.append("RECONSTRUCTED STEMMA:")
    lines.append("")
    lines.append(stemma_to_text(stemma))
    lines.append("")

    # Legend
    for node in stemma.nodes:
        if node.role == Classification.ARCHETYPE if False else False:
            pass
        if node.annotation:
            lines.append(f"  {node.label}  {node.annotation}")

    if stemma.contaminated:
        lines.append("")
        for wit in stemma.contaminated:
            lines.append(f"  ⚠ {wit} is a contaminated witness with MULTIPLE PARENTS")

    return "\n".join(lines)


def format_classifications(collation: CollationResult) -> str:
    """Format variant classifications as readable output."""
    lines: list[str] = []

    func_name = collation.witnesses[0].source if collation.witnesses else "unknown"
    lines.append(f"VARIANT CLASSIFICATION for {func_name}:")
    lines.append("")

    for unit in collation.variation_units:
        if not unit.is_variant or unit.classification is None:
            continue

        majority = unit.majority_reading
        if majority is None:
            continue

        for minority in unit.minority_readings:
            icon = CLASSIFICATION_ICONS.get(unit.classification, "?")
            label = CLASSIFICATION_LABELS.get(unit.classification, "UNKNOWN")

            lines.append(
                f"  L{unit.line_number}: {majority.text} → {minority.text} "
                f"(in {', '.join(minority.witnesses)})"
            )
            lines.append(f"    {icon} {label}")
            if unit.rationale:
                lines.append(f"    Evidence: {unit.rationale}")
            lines.append(f"    Confidence: {int(unit.confidence * 100)}%")
            lines.append("")

    return "\n".join(lines)


def format_archetype(archetype: ArchetypeResult, func_name: str = "unknown") -> str:
    """Format archetype reconstruction as readable output."""
    lines: list[str] = []

    lines.append(f"RECONSTRUCTED ARCHETYPE for {func_name}:")
    lines.append("")

    for i, line in enumerate(archetype.lines):
        line_num = i + 1
        annotation = archetype.annotations.get(line_num, "")
        annot_str = f"  # {annotation}" if annotation else ""
        lines.append(f"  {line_num:3d}  {line}{annot_str}")

    lines.append("")
    lines.append(
        f"  Method: {archetype.method} — prefer majority reading, "
        f"break ties with lectio difficilior, flag contaminated readings with ⚠"
    )
    lines.append("")
    lines.append(f"  Confidence: {int(archetype.confidence * 100)}%")

    return "\n".join(lines)


def format_contamination(reports: list[ContaminationReport]) -> str:
    """Format contamination detection results."""
    lines: list[str] = []

    lines.append("CONTAMINATED WITNESSES (code with multiple sources):")
    lines.append("")

    if not reports:
        lines.append("  No contaminated witnesses detected.")
    else:
        for report in reports:
            lines.append(f"  {report.witness}:")
            lines.append(f"    Primary lineage: {report.primary_lineage}")
            lines.append(f"    Contaminating source: {report.contaminating_source}")
            lines.append(f"    Mixing pattern: {report.mixing_pattern}")
            lines.append(f"    Likelihood: {report.likelihood}")
            lines.append("")
            lines.append(
                f"  ⚠ {report.witness} cannot be placed on a simple tree — "
                f"it's a hybrid"
            )
            lines.append(
                "  This means the stemma should be represented as a NETWORK, not a tree"
            )
            lines.append("")

    return "\n".join(lines)
