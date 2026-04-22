"""Pure Python Levenshtein distance implementation.

No external dependencies — implements the standard Wagner-Fischer algorithm.
"""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings.

    Uses the classic Wagner-Fischer dynamic programming algorithm.
    Time complexity: O(len(s1) * len(s2))
    Space complexity: O(min(len(s1), len(s2)))
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of substitution: 0 if same, 1 if different
            cost = 0 if c1 == c2 else 1
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + cost
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def normalized_distance(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein distance (0.0 = identical, 1.0 = completely different)."""
    if not s1 and not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    return levenshtein_distance(s1, s2) / max_len


def is_typosquat(name: str, known_names: list[str], max_distance: int = 2) -> list[tuple[str, int]]:
    """Check if a package name is a typosquat of any known package name.

    Returns list of (known_name, distance) for matches within max_distance.
    Excludes exact matches (distance=0) since that's the same package.
    """
    hits = []
    for known in known_names:
        dist = levenshtein_distance(name.lower(), known.lower())
        if 0 < dist <= max_distance:
            hits.append((known, dist))
    hits.sort(key=lambda x: x[1])
    return hits
