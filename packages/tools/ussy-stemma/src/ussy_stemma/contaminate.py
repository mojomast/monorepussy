"""Contamination detection — find code with multiple parents."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .models import (
    CollationResult,
    ContaminationReport,
    StemmaNode,
    StemmaTree,
    VariationUnit,
    WitnessRole,
)


def detect_contamination(
    collation: CollationResult,
    stemma: StemmaTree,
) -> list[ContaminationReport]:
    """Detect witnesses that have readings from multiple branches.

    A contaminated witness shares readings with witnesses from different
    branches of the stemma, suggesting it was copied from multiple sources.
    """
    if not collation.witnesses or not stemma.nodes:
        return []

    witnesses = collation.witnesses
    labels = [w.label for w in witnesses]

    # For each witness, track which branch each reading belongs to
    witness_branch_readings: dict[str, dict[str, set[int]]] = {}

    # Get branch assignments from ussy_stemma
    branches = _assign_branches(stemma)

    for unit in collation.variation_units:
        if not unit.is_variant:
            continue

        for reading in unit.readings:
            for wit_label in reading.witnesses:
                if wit_label not in witness_branch_readings:
                    witness_branch_readings[wit_label] = {}
                branch = branches.get(wit_label, "unknown")
                if branch not in witness_branch_readings[wit_label]:
                    witness_branch_readings[wit_label][branch] = set()
                witness_branch_readings[wit_label][branch].add(unit.line_number)

    # Also track which readings each witness shares with others
    reports: list[ContaminationReport] = []

    for wit_label in labels:
        if wit_label not in witness_branch_readings:
            continue

        branch_readings = witness_branch_readings[wit_label]
        if len(branch_readings) <= 1:
            continue

        # This witness has readings from multiple branches
        branches_sorted = sorted(
            branch_readings.items(),
            key=lambda x: -len(x[1]),
        )

        primary_branch = branches_sorted[0][0]
        contaminating_branch = branches_sorted[1][0]

        # Determine mixing pattern
        primary_count = len(branches_sorted[0][1])
        total_count = sum(len(v) for v in branch_readings.values())

        if total_count == 0:
            continue

        primary_ratio = primary_count / total_count
        if primary_ratio > 0.7:
            pattern = "Selective — occasional readings from other branch"
        elif primary_ratio > 0.4:
            pattern = "Mixed — significant readings from both branches"
        else:
            pattern = "Heavy mixing — nearly equal contribution from multiple branches"

        # Build likelihood description
        contaminating_lines = branches_sorted[1][1]
        if len(contaminating_lines) <= 2:
            likelihood = (
                f"Developer likely had access to both codebases and "
                f"cherry-picked {len(contaminating_lines)} line(s) from {contaminating_branch}"
            )
        else:
            likelihood = (
                f"Developer integrated substantial code from {contaminating_branch} "
                f"into primarily {primary_branch} codebase"
            )

        report = ContaminationReport(
            witness=wit_label,
            primary_lineage=primary_branch,
            contaminating_source=contaminating_branch,
            mixing_pattern=pattern,
            likelihood=likelihood,
        )
        reports.append(report)

    # Update stemma contaminated list
    for report in reports:
        if report.witness not in stemma.contaminated:
            stemma.contaminated.append(report.witness)

    return reports


def _assign_branches(stemma: StemmaTree) -> dict[str, str]:
    """Assign each terminal witness to a branch based on its parent in the stemma."""
    branches: dict[str, str] = {}

    def _walk(node: StemmaNode, branch: str) -> None:
        if node.role == WitnessRole.TERMINAL:
            branches[node.label] = branch
            return
        for i, child in enumerate(node.children):
            child_branch = child.label if child.role != WitnessRole.TERMINAL else branch
            _walk(child, child_branch)

    if stemma.root:
        _walk(stemma.root, stemma.root.label)

    return branches


def detect_contamination_from_collation(
    collation: CollationResult,
) -> list[ContaminationReport]:
    """Simpler contamination detection from collation alone (no stemma needed).

    A witness is contaminated if it sometimes agrees with one group and
    sometimes with another group on variant readings.
    """
    if len(collation.witnesses) < 3:
        return []

    labels = [w.label for w in collation.witnesses]

    # For each pair of witnesses, count shared minority readings
    shared_minority: dict[tuple[str, str], int] = defaultdict(int)
    for unit in collation.variation_units:
        if not unit.is_variant:
            continue
        for reading in unit.minority_readings:
            wits = reading.witnesses
            for i in range(len(wits)):
                for j in range(i + 1, len(wits)):
                    pair = tuple(sorted([wits[i], wits[j]]))
                    shared_minority[pair] += 1

    # For each witness, find which other witnesses it shares the most with
    witness_affinities: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (a, b), count in shared_minority.items():
        witness_affinities[a][b] += count
        witness_affinities[b][a] += count

    reports: list[ContaminationReport] = []

    for wit_label in labels:
        affinities = witness_affinities.get(wit_label, {})
        if len(affinities) < 2:
            continue

        sorted_affs = sorted(affinities.items(), key=lambda x: -x[1])

        # If the witness has significant affinity to multiple different groups
        top_count = sorted_affs[0][1]
        second_count = sorted_affs[1][1] if len(sorted_affs) > 1 else 0

        if top_count > 0 and second_count > 0 and second_count >= top_count * 0.3:
            primary = sorted_affs[0][0]
            secondary = sorted_affs[1][0]

            report = ContaminationReport(
                witness=wit_label,
                primary_lineage=f"shares most readings with {primary}",
                contaminating_source=f"also shares significant readings with {secondary}",
                mixing_pattern="Mixed affinity across branches",
                likelihood="Developer may have had access to multiple codebases",
            )
            reports.append(report)

    return reports
