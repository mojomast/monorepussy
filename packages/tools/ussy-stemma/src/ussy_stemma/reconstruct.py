"""Archetype reconstruction — build the 'original' code."""

from __future__ import annotations

from .models import (
    ArchetypeResult,
    Classification,
    CollationResult,
    StemmaTree,
    VariationUnit,
    WitnessRole,
)


def reconstruct_archetype(
    collation: CollationResult,
    prefer_witness: str | None = None,
) -> ArchetypeResult:
    """Reconstruct the archetype (most probable original code).

    Method: Lachmannian — prefer majority reading, break ties with
    lectio difficilior, flag contaminated readings.
    """
    if not collation.variation_units:
        return ArchetypeResult(confidence=1.0)

    lines: list[str] = []
    annotations: dict[int, str] = {}
    resolved = 0
    total_variant = 0

    for unit in collation.variation_units:
        line_idx = unit.line_number - 1  # 0-indexed

        if not unit.is_variant:
            # Unanimous reading — use it
            if unit.readings:
                lines.append(unit.readings[0].text)
            else:
                lines.append("")
            continue

        total_variant += 1
        majority = unit.majority_reading
        if majority is None:
            lines.append("")
            annotations[unit.line_number] = "No majority reading"
            continue

        # If a preferred witness is specified, use its reading
        if prefer_witness:
            for reading in unit.readings:
                if prefer_witness in reading.witnesses:
                    lines.append(reading.text)
                    if reading is not majority:
                        annotations[unit.line_number] = (
                            f"Following witness {prefer_witness} over majority"
                        )
                    resolved += 1
                    break
            else:
                lines.append(majority.text)
                resolved += 1
            continue

        # Use majority reading
        chosen = majority

        # If classification says majority is a scribal error, prefer lectio difficilior
        if unit.classification == Classification.SCRIBAL_ERROR:
            # Look for the reading that is more complex (lectio difficilior)
            for reading in unit.readings:
                if reading is not majority:
                    chosen = reading
                    annotations[unit.line_number] = (
                        f"Lectio difficilior: {reading.text} preferred over "
                        f"majority {majority.text} (scribal error)"
                    )
                    break
        elif unit.classification == Classification.CONSCIOUS_MODIFICATION:
            # Use majority for archetype; minority is conscious deviation
            chosen = majority
            annotations[unit.line_number] = (
                f"Majority reading; {', '.join(r.text for r in unit.minority_readings)} "
                f"is conscious modification"
            )
        elif unit.classification == Classification.AMBIGUOUS:
            chosen = majority
            annotations[unit.line_number] = "Ambiguous — majority reading used"
        else:
            chosen = majority

        lines.append(chosen.text)
        resolved += 1

    confidence = resolved / total_variant if total_variant > 0 else 1.0

    return ArchetypeResult(
        lines=lines,
        annotations=annotations,
        confidence=confidence,
        method="Lachmannian",
    )


def reconstruct_with_stemma(
    collation: CollationResult,
    stemma: StemmaTree,
    prefer_witness: str | None = None,
) -> ArchetypeResult:
    """Reconstruct archetype using stemma information.

    Uses the tree structure to inform which readings belong to which branch,
    producing a more accurate archetype.
    """
    # For now, delegate to basic reconstruction
    # A full implementation would traverse the tree to find archetype readings
    return reconstruct_archetype(collation, prefer_witness=prefer_witness)
