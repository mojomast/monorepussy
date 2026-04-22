"""Defect detection — find broken and accidental symmetry in code."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ussy_crystallo.models import (
    DefectReport,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
)


def detect_defects(
    fingerprints: list[StructuralFingerprint],
    relations: list[SymmetryRelation],
    similarity_threshold: float = 0.5,
) -> list[DefectReport]:
    """Detect broken symmetry and accidental symmetry defects.

    Broken symmetry: units that should mirror each other (shared base, high
    structural similarity) but diverge on specific methods/attributes.

    Accidental symmetry: high translational similarity without shared
    abstraction — classic copy-paste duplication.
    """
    defects: list[DefectReport] = []

    # Build name → fingerprint lookup
    name_to_fp: dict[str, StructuralFingerprint] = {}
    for fp in fingerprints:
        name_to_fp[fp.name] = fp

    for rel in relations:
        # --- Broken symmetry ---
        if rel.symmetry_type == SymmetryType.BROKEN and rel.similarity >= similarity_threshold:
            source_fp = name_to_fp.get(rel.source)
            target_fp = name_to_fp.get(rel.target)
            if source_fp and target_fp:
                defect = DefectReport(
                    file_path=source_fp.file_path,
                    unit_name=rel.source,
                    expected_symmetry_with=rel.target,
                    defect_type="broken",
                    missing_features=rel.missing_in_source,
                    extra_features=rel.extra_in_source,
                    confidence=rel.confidence,
                    suggestion=_broken_suggestion(source_fp, target_fp, rel),
                )
                defects.append(defect)

                # Also create one from the target's perspective
                defect2 = DefectReport(
                    file_path=target_fp.file_path,
                    unit_name=rel.target,
                    expected_symmetry_with=rel.source,
                    defect_type="broken",
                    missing_features=rel.missing_in_target,
                    extra_features=rel.extra_in_target,
                    confidence=rel.confidence,
                    suggestion=_broken_suggestion(target_fp, source_fp, rel),
                )
                defects.append(defect2)

        # --- Accidental symmetry ---
        if (
            rel.symmetry_type == SymmetryType.TRANSLATIONAL
            and rel.intent == SymmetryIntent.ACCIDENTAL
            and rel.similarity >= similarity_threshold
        ):
            source_fp = name_to_fp.get(rel.source)
            target_fp = name_to_fp.get(rel.target)
            if source_fp and target_fp:
                shared_methods = source_fp.method_set & target_fp.method_set
                defect = DefectReport(
                    file_path=source_fp.file_path,
                    unit_name=rel.source,
                    expected_symmetry_with=rel.target,
                    defect_type="accidental",
                    missing_features=[],
                    extra_features=[],
                    confidence=rel.confidence,
                    suggestion=(
                        f"Copy-paste candidate: {rel.source} and {rel.target} share "
                        f"{len(shared_methods)} methods without a common base class. "
                        f"Consider extracting a shared abstraction."
                    ),
                )
                defects.append(defect)

    # Also detect near-broken symmetry from rotational pairs with missing methods
    for rel in relations:
        if (
            rel.symmetry_type == SymmetryType.ROTATIONAL
            and rel.missing_in_target
            and rel.similarity >= 0.5
            and not any(d.unit_name == rel.source and d.expected_symmetry_with == rel.target for d in defects)
        ):
            source_fp = name_to_fp.get(rel.source)
            if source_fp:
                defect = DefectReport(
                    file_path=source_fp.file_path,
                    unit_name=rel.source,
                    expected_symmetry_with=rel.target,
                    defect_type="broken",
                    missing_features=[],
                    extra_features=rel.missing_in_source,
                    confidence=rel.confidence * 0.8,  # lower confidence
                    suggestion=(
                        f"{rel.source} has extra methods vs {rel.target}: "
                        f"{', '.join(rel.missing_in_source)}"
                    ),
                )
                defects.append(defect)

    # Deduplicate by (unit_name, expected_symmetry_with)
    seen: set[tuple[str, str, str]] = set()
    unique_defects: list[DefectReport] = []
    for d in defects:
        key = (d.unit_name, d.expected_symmetry_with, d.defect_type)
        if key not in seen:
            seen.add(key)
            unique_defects.append(d)

    return sorted(unique_defects, key=lambda d: d.confidence, reverse=True)


def detect_translational_groups(
    fingerprints: list[StructuralFingerprint],
    relations: list[SymmetryRelation],
    min_group_size: int = 3,
) -> list[DefectReport]:
    """Detect groups of 3+ units with translational (copy-paste) symmetry."""
    # Build adjacency for translational relations
    adjacency: dict[str, set[str]] = defaultdict(set)
    for rel in relations:
        if rel.symmetry_type == SymmetryType.TRANSLATIONAL:
            adjacency[rel.source].add(rel.target)
            adjacency[rel.target].add(rel.source)

    # Find connected components among translational links
    visited: set[str] = set()
    groups: list[list[str]] = []

    fp_names = {fp.name for fp in fingerprints}
    for fp in fingerprints:
        if fp.name in visited:
            continue
        component: list[str] = []
        queue = [fp.name]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited and neighbor in fp_names:
                    queue.append(neighbor)

        if len(component) >= min_group_size:
            groups.append(sorted(component))

    name_to_fp = {fp.name: fp for fp in fingerprints}

    reports: list[DefectReport] = []
    for group in groups:
        fps = [name_to_fp[n] for n in group if n in name_to_fp]
        if not fps:
            continue
        # Find shared methods across group
        method_sets = [fp.method_set for fp in fps]
        shared = method_sets[0]
        for ms in method_sets[1:]:
            shared = shared & ms

        # Compute average similarity
        from ussy_crystallo.similarity import compute_similarity
        if len(fps) >= 2:
            sims = []
            for i in range(len(fps)):
                for j in range(i + 1, len(fps)):
                    sims.append(compute_similarity(fps[i], fps[j]))
            avg_sim = sum(sims) / len(sims) if sims else 0.0
        else:
            avg_sim = 0.0

        # Determine if accidental
        has_shared_base = False
        if fps:
            base_sets = [set(fp.base_classes) for fp in fps]
            common_bases = base_sets[0]
            for bs in base_sets[1:]:
                common_bases = common_bases & bs
            has_shared_base = bool(common_bases)

        defect_type = "accidental" if not has_shared_base else "intentional"
        suggestion = ""
        if defect_type == "accidental":
            suggestion = (
                f"{len(fps)} units share {len(shared)} methods without a common base. "
                f"Consider extracting a shared abstraction or mixin."
            )
        else:
            suggestion = (
                f"{len(fps)} units share a common base and {len(shared)} methods. "
                f"Translational symmetry appears intentional."
            )

        report = DefectReport(
            file_path=fps[0].file_path if fps else "",
            unit_name=fps[0].name if fps else "",
            expected_symmetry_with=", ".join(group[1:]),
            defect_type=defect_type,
            missing_features=[],
            extra_features=[],
            confidence=round(avg_sim, 4),
            suggestion=suggestion,
        )
        reports.append(report)

    return reports


def _broken_suggestion(
    source: StructuralFingerprint,
    target: StructuralFingerprint,
    rel: SymmetryRelation,
) -> str:
    """Generate a human-readable suggestion for broken symmetry."""
    parts: list[str] = []
    if rel.missing_in_source:
        parts.append(f"Missing in {source.name}: {', '.join(rel.missing_in_source)}")
    if rel.missing_in_target:
        parts.append(f"Missing in {target.name}: {', '.join(rel.missing_in_target)}")
    if rel.extra_in_source:
        parts.append(f"Extra in {source.name}: {', '.join(rel.extra_in_source)}")
    if rel.extra_in_target:
        parts.append(f"Extra in {target.name}: {', '.join(rel.extra_in_target)}")

    shared_bases = set(source.base_classes) & set(target.base_classes)
    if shared_bases:
        parts.append(f"Shared base: {', '.join(shared_bases)}")

    return "; ".join(parts) if parts else "Structural divergence detected."
