"""Report formatting — human-readable output for Crystallo results."""

from __future__ import annotations

from crystallo.models import (
    DefectReport,
    ModuleClassification,
    SpaceGroup,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
    UnitCell,
)


# ---------------------------------------------------------------------------
# Symmetry-type short codes
# ---------------------------------------------------------------------------

_SYM_TYPE_SHORT = {
    SymmetryType.ROTATIONAL: "Cn",
    SymmetryType.REFLECTION: "σ",
    SymmetryType.TRANSLATIONAL: "T",
    SymmetryType.GLIDE: "g",
    SymmetryType.BROKEN: "⚠",
    SymmetryType.NONE: "—",
}

_INTENT_SHORT = {
    SymmetryIntent.INTENTIONAL: "INTENTIONAL",
    SymmetryIntent.ACCIDENTAL: "ACCIDENTAL",
    SymmetryIntent.EXPECTED: "EXPECTED",
    SymmetryIntent.BROKEN: "BROKEN",
    SymmetryIntent.UNKNOWN: "UNKNOWN",
}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_symmetry_relations(relations: list[SymmetryRelation]) -> str:
    """Format a list of symmetry relations for terminal output."""
    if not relations:
        return "No significant symmetry detected.\n"

    lines: list[str] = []
    for rel in relations:
        sym_code = _SYM_TYPE_SHORT.get(rel.symmetry_type, "?")
        intent_str = _INTENT_SHORT.get(rel.intent, "?")
        line = (
            f"{sym_code} {rel.source} ↔ {rel.target}  "
            f"[{intent_str}]  similarity={rel.similarity:.2f}"
        )
        if rel.missing_in_target:
            line += f"\n    Missing in {rel.target}: {', '.join(rel.missing_in_target)}"
        if rel.missing_in_source:
            line += f"\n    Missing in {rel.source}: {', '.join(rel.missing_in_source)}"
        lines.append(line)

    return "\n".join(lines) + "\n"


def format_unit_cells(unit_cells: list[UnitCell]) -> str:
    """Format unit cell summary for terminal output."""
    if not unit_cells:
        return "No repeating structural patterns found.\n"

    lines: list[str] = []
    for uc in unit_cells:
        lines.append(f"Unit cell: {uc.representative_name}")
        lines.append(f"  Space group: {uc.space_group.value}")
        lines.append(f"  Symmetry type: {uc.symmetry_type.name}")
        lines.append(f"  Members ({uc.member_count}): {', '.join(uc.member_names)}")
        lines.append(f"  Avg similarity: {uc.avg_similarity:.2f}")
        lines.append("")

    return "\n".join(lines)


def format_defects(defects: list[DefectReport]) -> str:
    """Format defect report for terminal output."""
    if not defects:
        return "No symmetry defects found.\n"

    broken = [d for d in defects if d.defect_type == "broken"]
    accidental = [d for d in defects if d.defect_type == "accidental"]

    lines: list[str] = []

    if broken:
        lines.append("BROKEN SYMMETRY DEFECTS:")
        lines.append("=" * 60)
        for d in broken:
            lines.append(f"  ⚠  {d.unit_name}")
            lines.append(f"     Expected symmetry with: {d.expected_symmetry_with}")
            if d.missing_features:
                lines.append(f"     Missing: {', '.join(d.missing_features)}")
            if d.extra_features:
                lines.append(f"     Extra: {', '.join(d.extra_features)}")
            lines.append(f"     Confidence: {d.confidence:.2f}")
            if d.suggestion:
                lines.append(f"     {d.suggestion}")
            lines.append("")

    if accidental:
        lines.append("ACCIDENTAL SYMMETRY (copy-paste candidates):")
        lines.append("=" * 60)
        for d in accidental:
            lines.append(f"  📋 {d.unit_name} ↔ {d.expected_symmetry_with}")
            lines.append(f"     Confidence: {d.confidence:.2f}")
            if d.suggestion:
                lines.append(f"     {d.suggestion}")
            lines.append("")

    return "\n".join(lines)


def format_classification(classification: ModuleClassification) -> str:
    """Format a module classification for terminal output."""
    lines: list[str] = [
        f"{classification.path}  →  {classification.space_group.value}",
        f"  {classification.symmetry_description}",
        f"  Structural units: {classification.fingerprint_count}",
        f"  Rotational pairs: {classification.rotational_pairs}",
        f"  Reflection pairs: {classification.reflection_pairs}",
        f"  Translational groups: {classification.translational_groups}",
        f"  Broken symmetry: {classification.broken_count}",
    ]
    return "\n".join(lines) + "\n"


def format_fingerprint_summary(fingerprints: list[StructuralFingerprint]) -> str:
    """Format a summary of extracted fingerprints."""
    if not fingerprints:
        return "No structural units found.\n"

    lines: list[str] = [f"Extracted {len(fingerprints)} structural unit(s):\n"]
    for fp in fingerprints:
        kind_icon = "◆" if fp.kind == "class" else "○"
        lines.append(f"  {kind_icon} {fp.name} ({fp.kind})")
        if fp.kind == "class":
            lines.append(f"    Methods: {', '.join(fp.method_names) if fp.method_names else '(none)'}")
            if fp.base_classes:
                lines.append(f"    Bases: {', '.join(fp.base_classes)}")
            if fp.attribute_names:
                lines.append(f"    Attributes: {', '.join(fp.attribute_names)}")
        else:
            if fp.method_signatures:
                sig = fp.method_signatures[0]
                lines.append(f"    Args: {sig.arg_count}, async={sig.is_async}")
        lines.append("")

    return "\n".join(lines)
