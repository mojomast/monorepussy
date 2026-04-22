"""Compatibility analysis — Scion/Rootstock API Surface Match Score."""

from __future__ import annotations

from ussy_cambium.extractor import InterfaceInfo, extract_interface, extract_interface_from_file
from ussy_cambium.models import CompatibilityScore, DependencyPair


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity: |A∩B| / |A∪B|."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    intersection = set_a & set_b
    return len(intersection) / len(union)


def compute_type_similarity(consumer: InterfaceInfo, provider: InterfaceInfo) -> float:
    """Φ(δ_tax) — Jaccard similarity of exported types."""
    consumer_types = consumer.exported_types | consumer.exported_functions
    provider_types = provider.exported_types | provider.exported_functions
    return jaccard_similarity(consumer_types, provider_types)


def compute_precondition_satisfaction(consumer: InterfaceInfo, provider: InterfaceInfo) -> float:
    """β_recog — Fraction of provider preconditions satisfied by consumer.

    Heuristic: check if consumer's exported names cover provider's preconditions.
    """
    if not provider.preconditions:
        return 1.0  # no preconditions to satisfy

    consumer_capabilities = consumer.exported_types | consumer.exported_functions
    satisfied = sum(1 for p in provider.preconditions if p in consumer_capabilities)
    return satisfied / len(provider.preconditions)


def compute_version_overlap(consumer_range: tuple[str, str], provider_range: tuple[str, str]) -> float:
    """ψ_phen — Version range overlap.

    Simplified: compare version strings numerically.
    Returns |range_a ∩ range_b| / |range_a ∪ range_b|.
    """
    try:
        c_lo, c_hi = _parse_version_range(consumer_range)
        p_lo, p_hi = _parse_version_range(provider_range)

        overlap_lo = max(c_lo, p_lo)
        overlap_hi = min(c_hi, p_hi)

        if overlap_hi <= overlap_lo:
            return 0.0

        union_lo = min(c_lo, p_lo)
        union_hi = max(c_hi, p_hi)

        overlap = overlap_hi - overlap_lo
        union = union_hi - union_lo

        if union == 0:
            return 1.0

        return overlap / union
    except (ValueError, TypeError):
        return 0.0


def _parse_version_range(vrange: tuple[str, str]) -> tuple[float, float]:
    """Parse version range strings to numeric tuples."""
    lo = _version_to_float(vrange[0])
    hi = _version_to_float(vrange[1])
    return (lo, hi)


def _version_to_float(v: str) -> float:
    """Convert a version string like '2.3.1' to a float for comparison."""
    parts = v.strip().split(".")
    if not parts:
        return 0.0
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return major + minor * 0.01 + patch * 0.0001
    except (ValueError, IndexError):
        return 0.0


def compute_compatibility(
    consumer: InterfaceInfo,
    provider: InterfaceInfo,
    consumer_version_range: tuple[str, str] | None = None,
    provider_version_range: tuple[str, str] | None = None,
) -> CompatibilityScore:
    """Compute full scion/rootstock compatibility score."""
    type_sim = compute_type_similarity(consumer, provider)
    precond_sat = compute_precondition_satisfaction(consumer, provider)

    if consumer_version_range and provider_version_range:
        version_overlap = compute_version_overlap(consumer_version_range, provider_version_range)
    else:
        version_overlap = 1.0  # assume compatible if no version info

    return CompatibilityScore(
        type_similarity=type_sim,
        precondition_satisfaction=precond_sat,
        version_overlap=version_overlap,
    )


def compute_compatibility_from_source(
    consumer_source: str,
    provider_source: str,
    consumer_name: str = "consumer",
    provider_name: str = "provider",
) -> CompatibilityScore:
    """Compute compatibility from source code strings."""
    consumer = extract_interface(consumer_source, consumer_name)
    provider = extract_interface(provider_source, provider_name)
    return compute_compatibility(consumer, provider)


def compute_compatibility_from_files(
    consumer_path: str,
    provider_path: str,
) -> CompatibilityScore:
    """Compute compatibility from file paths."""
    consumer = extract_interface_from_file(consumer_path)
    provider = extract_interface_from_file(provider_path)
    return compute_compatibility(consumer, provider)
