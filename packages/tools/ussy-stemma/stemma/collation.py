"""Collation engine — align all variants and identify every difference."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .alignment import align_witnesses, pairwise_distance
from .models import (
    CollationResult,
    Reading,
    VariantType,
    VariationUnit,
    Witness,
    normalize_line,
)


def load_witnesses(path: Path) -> list[Witness]:
    """Load witness files from a path (file or directory).

    If given a directory, recursively find all .py files.
    Each file becomes a witness.
    """
    witnesses: list[Witness] = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.rglob("*.py"))
    else:
        return witnesses

    for i, fpath in enumerate(files):
        label = chr(ord("A") + i) if i < 26 else f"W{i}"
        try:
            content = fpath.read_text(encoding="utf-8")
            lines = content.splitlines()
            witness = Witness(
                label=label,
                source=str(fpath),
                lines=lines,
            )
            witnesses.append(witness)
        except (OSError, UnicodeDecodeError):
            continue

    return witnesses


def load_witnesses_from_strings(
    sources: dict[str, str],
) -> list[Witness]:
    """Load witnesses from label->source_code mapping."""
    witnesses: list[Witness] = []
    for label, code in sources.items():
        lines = code.splitlines()
        witness = Witness(
            label=label,
            source=f"<{label}>",
            lines=lines,
        )
        witnesses.append(witness)
    return witnesses


def identify_variation_units(
    aligned: dict[int, dict[str, str]],
    witnesses: list[Witness],
) -> list[VariationUnit]:
    """Identify positions where witnesses disagree."""
    units: list[VariationUnit] = []
    labels = [w.label for w in witnesses]

    for pos in sorted(aligned.keys()):
        readings_map: dict[str, list[str]] = {}  # text -> list of witness labels

        for label in labels:
            text = aligned[pos].get(label, "")
            # Normalize for grouping
            norm_text = normalize_line(text) if text else "(absent)"
            if norm_text not in readings_map:
                readings_map[norm_text] = []
            readings_map[norm_text].append(label)

        total_witnesses = len(witnesses)

        readings: list[Reading] = []
        for text, wit_labels in readings_map.items():
            if text == "(absent)":
                vtype = VariantType.OMISSION
            elif len(wit_labels) == total_witnesses:
                vtype = VariantType.UNANIMOUS
            elif len(wit_labels) > total_witnesses / 2:
                vtype = VariantType.MAJORITY
            else:
                vtype = VariantType.VARIANT

            readings.append(Reading(
                text=text,
                witnesses=wit_labels,
                variant_type=vtype,
            ))

        # Sort: majority first, then by count
        readings.sort(key=lambda r: (-r.witness_count, r.text))

        unit = VariationUnit(
            line_number=pos + 1,  # 1-indexed
            readings=readings,
        )
        units.append(unit)

    return units


def collate(witnesses: list[Witness]) -> CollationResult:
    """Collate witnesses: align and identify variation units."""
    if not witnesses:
        return CollationResult()

    # Align all witnesses
    aligned = align_witnesses(witnesses)

    # Identify variation units
    variation_units = identify_variation_units(aligned, witnesses)

    return CollationResult(
        witnesses=witnesses,
        variation_units=variation_units,
        aligned_lines=aligned,
    )


def collate_path(path: Path) -> CollationResult:
    """Collate witnesses from a file path or directory."""
    witnesses = load_witnesses(path)
    return collate(witnesses)
