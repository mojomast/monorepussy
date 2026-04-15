"""Sequence alignment for code variants using Needleman-Wunsch."""

from __future__ import annotations

from .models import Witness, normalize_line

# Gap penalty for alignment
GAP_PENALTY = -2
# Match score
MATCH_SCORE = 2
# Mismatch score
MISMATCH_PENALTY = -1


def line_similarity(a: str, b: str) -> float:
    """Compute similarity between two normalized code lines (0.0 to 1.0)."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0

    # Word-level similarity using Jaccard
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def needleman_wunsch(
    seq_a: list[str],
    seq_b: list[str],
    gap_penalty: int = GAP_PENALTY,
    match_score: int = MATCH_SCORE,
    mismatch_penalty: int = MISMATCH_PENALTY,
) -> tuple[list[tuple[Optional[int], Optional[int]]], int]:
    """Needleman-Wunsch global alignment for two line sequences.

    Returns alignment pairs and total score.
    Each pair is (index_in_a, index_in_b) where None means a gap.
    """
    n = len(seq_a)
    m = len(seq_b)

    # Score matrix
    score = [[0] * (m + 1) for _ in range(n + 1)]
    # Traceback
    trace = [[0] * (m + 1) for _ in range(n + 1)]  # 0=diag, 1=up, 2=left

    # Initialize
    for i in range(1, n + 1):
        score[i][0] = i * gap_penalty
        trace[i][0] = 1
    for j in range(1, m + 1):
        score[0][j] = j * gap_penalty
        trace[0][j] = 2

    # Fill
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sim = line_similarity(seq_a[i - 1], seq_b[j - 1])
            if sim > 0.5:
                s = match_score
            else:
                s = mismatch_penalty

            diag = score[i - 1][j - 1] + s
            up = score[i - 1][j] + gap_penalty
            left = score[i][j - 1] + gap_penalty

            best = max(diag, up, left)
            score[i][j] = best
            if best == diag:
                trace[i][j] = 0
            elif best == up:
                trace[i][j] = 1
            else:
                trace[i][j] = 2

    # Traceback
    alignment: list[tuple[Optional[int], Optional[int]]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and trace[i][j] == 0:
            alignment.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or trace[i][j] == 1):
            alignment.append((i - 1, None))
            i -= 1
        else:
            alignment.append((None, j - 1))
            j -= 1

    alignment.reverse()
    return alignment, score[n][m]


def align_witnesses(
    witnesses: list[Witness],
) -> dict[int, dict[str, str]]:
    """Align multiple witnesses using progressive alignment.

    Returns a mapping: aligned_position -> {witness_label -> line_text}.
    Gaps are represented by empty string.
    """
    if not witnesses:
        return {}

    if len(witnesses) == 1:
        return {i: {witnesses[0].label: line} for i, line in enumerate(witnesses[0].normalized_lines)}

    # Use the first witness as reference, align others progressively
    ref = witnesses[0]
    aligned: dict[int, dict[str, str]] = {
        i: {ref.label: line} for i, line in enumerate(ref.normalized_lines)
    }

    for wit in witnesses[1:]:
        ref_lines = [aligned[i].get(ref.label, "") for i in sorted(aligned.keys())]
        new_lines = wit.normalized_lines

        pairs, _ = needleman_wunsch(ref_lines, new_lines)

        # Build new aligned dict
        new_aligned: dict[int, dict[str, str]] = {}
        for pos, (ri, ni) in enumerate(pairs):
            if pos not in new_aligned:
                new_aligned[pos] = {}
            # Copy existing witnesses
            for existing_pos in sorted(aligned.keys()):
                if existing_pos == ri:
                    for label, text in aligned[existing_pos].items():
                        new_aligned[pos][label] = text
                    break
            # Add new witness
            new_aligned[pos][wit.label] = new_lines[ni] if ni is not None else ""

        # If new alignment has more positions, fill in gaps for existing witnesses
        all_labels = [w.label for w in witnesses[:witnesses.index(wit) + 1]]
        for pos in new_aligned:
            for label in all_labels:
                if label not in new_aligned[pos]:
                    new_aligned[pos][label] = ""

        aligned = new_aligned

    return aligned


def pairwise_distance(wit_a: Witness, wit_b: Witness) -> float:
    """Compute normalized edit distance between two witnesses (0.0=identical, 1.0=completely different)."""
    pairs, _ = needleman_wunsch(wit_a.normalized_lines, wit_b.normalized_lines)

    if not pairs:
        return 0.0

    mismatches = 0
    total = len(pairs)
    for ai, bi in pairs:
        if ai is None or bi is None:
            mismatches += 1
        else:
            sim = line_similarity(wit_a.normalized_lines[ai], wit_b.normalized_lines[bi])
            if sim < 1.0:
                mismatches += 1 - sim

    return mismatches / total if total > 0 else 0.0
