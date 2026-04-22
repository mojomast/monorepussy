"""Space group classification — assign crystallographic groups to code modules."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ussy_crystallo.models import (
    ModuleClassification,
    SpaceGroup,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
    UnitCell,
)
from ussy_crystallo.similarity import (
    compute_pairwise_similarities,
    compute_similarity,
    jaccard_index,
)


def classify_module(
    directory: str | Path,
    fingerprints: list[StructuralFingerprint],
    relations: list[SymmetryRelation],
) -> ModuleClassification:
    """Classify a module's structural identity into a space group."""
    directory = str(directory)

    rotational = sum(1 for r in relations if r.symmetry_type == SymmetryType.ROTATIONAL)
    reflection = sum(1 for r in relations if r.symmetry_type == SymmetryType.REFLECTION)
    translational = sum(1 for r in relations if r.symmetry_type == SymmetryType.TRANSLATIONAL)
    glide = sum(1 for r in relations if r.symmetry_type == SymmetryType.GLIDE)
    broken = sum(1 for r in relations if r.symmetry_type == SymmetryType.BROKEN)

    space_group = _assign_space_group(
        len(fingerprints), rotational, reflection, translational, glide, broken
    )

    desc = _describe_symmetry(space_group, rotational, reflection, translational, glide, broken)

    return ModuleClassification(
        path=directory,
        space_group=space_group,
        symmetry_description=desc,
        fingerprint_count=len(fingerprints),
        rotational_pairs=rotational,
        reflection_pairs=reflection,
        translational_groups=translational,
        broken_count=broken,
    )


def _assign_space_group(
    n_units: int,
    rotational: int,
    reflection: int,
    translational: int,
    glide: int,
    broken: int,
) -> SpaceGroup:
    """Heuristic assignment of space group based on detected symmetry counts."""
    total_sym = rotational + reflection + translational + glide

    if n_units == 0:
        return SpaceGroup.P1

    # High symmetry on multiple axes → cubic
    if rotational >= 3 and reflection >= 2 and translational >= 2:
        return SpaceGroup.Pa3

    # 4-fold rotational → tetragonal
    if rotational >= 4:
        return SpaceGroup.P4

    # High translational → hexagonal
    if translational >= 3:
        return SpaceGroup.P6

    # Reflection dominant → monoclinic Pm
    if reflection >= 1 and rotational == 0 and translational < 2:
        return SpaceGroup.Pm

    # Rotational dominant → monoclinic P2
    if rotational >= 1 and reflection == 0 and translational < 2:
        return SpaceGroup.P2

    # Both rotation and reflection → P2/m
    if rotational >= 1 and reflection >= 1:
        return SpaceGroup.P2m

    # Glide symmetry → monoclinic
    if glide >= 1:
        return SpaceGroup.Pm

    # Low total symmetry → triclinic P1
    if total_sym <= 1 or broken > total_sym:
        return SpaceGroup.P1

    return SpaceGroup.P1


def _describe_symmetry(
    group: SpaceGroup,
    rotational: int,
    reflection: int,
    translational: int,
    glide: int,
    broken: int,
) -> str:
    """Human-readable description of the classification."""
    parts: list[str] = []
    crystal_system = _crystal_system_name(group)
    parts.append(f"{crystal_system} system")

    if rotational:
        parts.append(f"{rotational} rotational pair(s)")
    if reflection:
        parts.append(f"{reflection} reflection pair(s)")
    if translational:
        parts.append(f"{translational} translational group(s)")
    if glide:
        parts.append(f"{glide} glide pair(s)")
    if broken:
        parts.append(f"{broken} broken symmetry")

    return "; ".join(parts)


def _crystal_system_name(group: SpaceGroup) -> str:
    """Map space group to crystal system name."""
    match group:
        case SpaceGroup.P1:
            return "Triclinic"
        case SpaceGroup.Pm | SpaceGroup.P2 | SpaceGroup.P2m:
            return "Monoclinic"
        case SpaceGroup.P4:
            return "Tetragonal"
        case SpaceGroup.P6:
            return "Hexagonal"
        case SpaceGroup.Pa3:
            return "Cubic"


# ---------------------------------------------------------------------------
# Unit cell detection
# ---------------------------------------------------------------------------

def detect_unit_cells(
    fingerprints: list[StructuralFingerprint],
    relations: list[SymmetryRelation],
    min_cluster_size: int = 2,
) -> list[UnitCell]:
    """Cluster fingerprints into unit cells (repeating structural patterns)."""
    if not fingerprints:
        return []

    # Build adjacency: fingerprints connected by significant similarity
    adjacency: dict[str, set[str]] = defaultdict(set)
    for rel in relations:
        if rel.similarity >= 0.4:
            adjacency[rel.source].add(rel.target)
            adjacency[rel.target].add(rel.source)

    # Simple connected-component clustering via BFS
    visited: set[str] = set()
    clusters: list[list[str]] = []

    name_to_fp: dict[str, StructuralFingerprint] = {fp.name: fp for fp in fingerprints}

    for fp in fingerprints:
        if fp.name in visited:
            continue
        # BFS from this node
        component: list[str] = []
        queue = [fp.name]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited and neighbor in name_to_fp:
                    queue.append(neighbor)

        if len(component) >= min_cluster_size:
            clusters.append(component)

    # Build UnitCell objects from clusters
    unit_cells: list[UnitCell] = []
    for cluster in clusters:
        fps = [name_to_fp[n] for n in cluster if n in name_to_fp]
        if not fps:
            continue
        # Representative is the one with the most methods
        representative = max(fps, key=lambda f: len(f.method_names))

        # Determine dominant symmetry type among cluster members
        cluster_set = set(cluster)
        cluster_rels = [
            r for r in relations
            if r.source in cluster_set and r.target in cluster_set
        ]
        if cluster_rels:
            type_counts = Counter(r.symmetry_type for r in cluster_rels)
            dominant_type = type_counts.most_common(1)[0][0]
        else:
            dominant_type = SymmetryType.NONE

        # Compute average pairwise similarity within cluster
        if len(fps) >= 2:
            pair_sims = []
            for i in range(len(fps)):
                for j in range(i + 1, len(fps)):
                    pair_sims.append(compute_similarity(fps[i], fps[j]))
            avg_sim = sum(pair_sims) / len(pair_sims) if pair_sims else 0.0
        else:
            avg_sim = 0.0

        # Determine space group for this unit cell
        rot = sum(1 for r in cluster_rels if r.symmetry_type == SymmetryType.ROTATIONAL)
        ref = sum(1 for r in cluster_rels if r.symmetry_type == SymmetryType.REFLECTION)
        tra = sum(1 for r in cluster_rels if r.symmetry_type == SymmetryType.TRANSLATIONAL)
        gli = sum(1 for r in cluster_rels if r.symmetry_type == SymmetryType.GLIDE)
        brk = sum(1 for r in cluster_rels if r.symmetry_type == SymmetryType.BROKEN)
        sg = _assign_space_group(len(fps), rot, ref, tra, gli, brk)

        uc = UnitCell(
            representative_name=representative.name,
            member_names=cluster,
            member_fingerprints=fps,
            symmetry_type=dominant_type,
            space_group=sg,
            member_count=len(cluster),
            avg_similarity=round(avg_sim, 4),
        )
        unit_cells.append(uc)

    return unit_cells
