"""Distance metrics for comparing feature vectors.

Implements Euclidean and Hamming distance metrics using only stdlib.
"""

import math
from typing import List


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """Compute Euclidean distance between two feature vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector lengths differ: {len(a)} vs {len(b)}")
    total = 0.0
    for x, y in zip(a, b):
        diff = x - y
        total += diff * diff
    return math.sqrt(total)


def manhattan_distance(a: List[float], b: List[float]) -> float:
    """Compute Manhattan (L1) distance between two feature vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector lengths differ: {len(a)} vs {len(b)}")
    total = 0.0
    for x, y in zip(a, b):
        total += abs(x - y)
    return total


def hamming_distance(a: List[float], b: List[float], threshold: float = 0.3) -> float:
    """Compute normalized Hamming distance (fraction of differing dimensions).

    Two dimensions differ if their absolute difference exceeds threshold.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector lengths differ: {len(a)} vs {len(b)}")
    if not a:
        return 0.0
    differing = sum(1 for x, y in zip(a, b) if abs(x - y) > threshold)
    return differing / len(a)


def cosine_distance(a: List[float], b: List[float]) -> float:
    """Compute cosine distance (1 - cosine_similarity) between two vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector lengths differ: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 1.0
    similarity = dot / (mag_a * mag_b)
    # Clamp to [-1, 1] for floating point safety
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def weighted_euclidean_distance(a: List[float], b: List[float],
                                 weights: List[float]) -> float:
    """Compute weighted Euclidean distance."""
    if len(a) != len(b) or len(a) != len(weights):
        raise ValueError("Vector and weight lengths must match")
    total = 0.0
    for x, y, w in zip(a, b, weights):
        diff = x - y
        total += w * diff * diff
    return math.sqrt(total)


def min_distance_to_corpus(vector: List[float], corpus: List[List[float]],
                            metric: str = "euclidean") -> float:
    """Find the minimum distance from a vector to any vector in a corpus.

    Args:
        vector: Query vector
        corpus: List of corpus vectors
        metric: Distance metric name ('euclidean', 'manhattan', 'hamming', 'cosine')

    Returns:
        Minimum distance to any corpus vector
    """
    if not corpus:
        return float('inf')

    dist_fn = _get_distance_fn(metric)
    min_dist = float('inf')
    for corpus_vec in corpus:
        d = dist_fn(vector, corpus_vec)
        if d < min_dist:
            min_dist = d
    return min_dist


def _get_distance_fn(metric: str):
    """Get distance function by name."""
    metrics = {
        'euclidean': euclidean_distance,
        'manhattan': manhattan_distance,
        'hamming': hamming_distance,
        'cosine': cosine_distance,
    }
    if metric not in metrics:
        raise ValueError(f"Unknown metric: {metric}. Choose from {list(metrics.keys())}")
    return metrics[metric]
