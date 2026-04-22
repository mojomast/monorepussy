"""Alignment analysis — Interface Cambium Alignment Score."""

from __future__ import annotations

from cambium.extractor import InterfaceInfo, extract_interface, extract_interface_from_file
from cambium.models import AlignmentScore


def compute_name_match(consumer: InterfaceInfo, provider: InterfaceInfo) -> float:
    """A_name — method/attribute name matching ratio (surface contact).

    Fraction of consumer's required names that are present in provider.
    """
    consumer_names = consumer.exported_types | consumer.exported_functions
    provider_names = provider.exported_types | provider.exported_functions

    # Also check method names within classes
    consumer_methods = set()
    for sig_name in consumer.method_signatures:
        if "." in sig_name:
            consumer_methods.add(sig_name.split(".", 1)[1])
        else:
            consumer_methods.add(sig_name)

    provider_methods = set()
    for sig_name in provider.method_signatures:
        if "." in sig_name:
            provider_methods.add(sig_name.split(".", 1)[1])
        else:
            provider_methods.add(sig_name)

    all_consumer = consumer_names | consumer_methods
    all_provider = provider_names | provider_methods

    if not all_consumer:
        return 1.0  # no requirements = fully matched

    matched = all_consumer & all_provider
    return len(matched) / len(all_consumer)


def compute_signature_match(consumer: InterfaceInfo, provider: InterfaceInfo) -> float:
    """A_signature — parameter type/count matching (signature alignment).

    Compare method signatures between consumer expectations and provider offerings.
    """
    if not consumer.method_signatures:
        return 1.0  # no signatures to check

    total_score = 0.0
    count = 0

    for name, consumer_sig in consumer.method_signatures.items():
        provider_sig = provider.method_signatures.get(name)
        if provider_sig is None:
            # Try matching by method name (after the dot)
            base_name = name.split(".", 1)[-1] if "." in name else name
            for p_name, p_sig in provider.method_signatures.items():
                p_base = p_name.split(".", 1)[-1] if "." in p_name else p_name
                if p_base == base_name:
                    provider_sig = p_sig
                    break

        if provider_sig is None:
            # No matching method — zero signature match
            total_score += 0.0
        else:
            # Compare parameter counts and names
            score = _compare_signatures(consumer_sig, provider_sig)
            total_score += score

        count += 1

    return total_score / count if count > 0 else 1.0


def _compare_signatures(sig_a: list[str], sig_b: list[str]) -> float:
    """Compare two method signatures. Returns 0-1 similarity."""
    if not sig_a and not sig_b:
        return 1.0

    # Compare by count
    count_diff = abs(len(sig_a) - len(sig_b))
    max_len = max(len(sig_a), len(sig_b))
    count_score = 1.0 - (count_diff / max_len) if max_len > 0 else 1.0

    # Compare by name overlap
    names_a = {p.split(":")[0].strip("*") for p in sig_a}
    names_b = {p.split(":")[0].strip("*") for p in sig_b}
    if names_a | names_b:
        name_score = len(names_a & names_b) / len(names_a | names_b)
    else:
        name_score = 1.0

    return 0.5 * count_score + 0.5 * name_score


def compute_semantic_match(
    consumer: InterfaceInfo,
    provider: InterfaceInfo,
    error_congruence: float = 0.8,
    ordering_guarantees: float = 0.8,
    side_effect_congruence: float = 0.8,
) -> float:
    """A_semantic — behavioral contract alignment.

    Since we can't fully determine semantics from AST alone, we use heuristics:
    - Presence of matching error-raising patterns
    - Matching return type annotations (ordering guarantees)
    - Shared precondition patterns (side-effect congruence)

    When no semantic data is available, defaults to the provided estimates.
    """
    scores: list[float] = []

    # Heuristic 1: preconditions overlap suggests shared behavioral contracts
    if consumer.preconditions or provider.preconditions:
        consumer_precons = set(consumer.preconditions)
        provider_precons = set(provider.preconditions)
        if consumer_precons | provider_precons:
            overlap = len(consumer_precons & provider_precons) / len(consumer_precons | provider_precons)
            scores.append(overlap)

    # Heuristic 2: type annotation richness suggests contract formality
    consumer_typed = sum(1 for s in consumer.method_signatures.values() if any(":" in p for p in s))
    provider_typed = sum(1 for s in provider.method_signatures.values() if any(":" in p for p in s))
    consumer_total = len(consumer.method_signatures)
    provider_total = len(provider.method_signatures)

    if consumer_total > 0 or provider_total > 0:
        consumer_formality = consumer_typed / consumer_total if consumer_total > 0 else 0.5
        provider_formality = provider_typed / provider_total if provider_total > 0 else 0.5
        # Higher formality on both sides suggests better semantic alignment
        formality_score = (consumer_formality + provider_formality) / 2.0
        scores.append(formality_score)

    if not scores:
        # No semantic data available — use default estimates
        return (error_congruence + ordering_guarantees + side_effect_congruence) / 3.0

    return sum(scores) / len(scores)


def compute_alignment(
    consumer: InterfaceInfo,
    provider: InterfaceInfo,
) -> AlignmentScore:
    """Compute full cambium alignment score."""
    name_match = compute_name_match(consumer, provider)
    sig_match = compute_signature_match(consumer, provider)
    sem_match = compute_semantic_match(consumer, provider)

    return AlignmentScore(
        name_match=name_match,
        signature_match=sig_match,
        semantic_match=sem_match,
    )


def compute_alignment_from_source(
    consumer_source: str,
    provider_source: str,
    consumer_name: str = "consumer",
    provider_name: str = "provider",
) -> AlignmentScore:
    """Compute alignment from source code strings."""
    consumer = extract_interface(consumer_source, consumer_name)
    provider = extract_interface(provider_source, provider_name)
    return compute_alignment(consumer, provider)


def compute_alignment_from_files(
    consumer_path: str,
    provider_path: str,
) -> AlignmentScore:
    """Compute alignment from file paths."""
    consumer = extract_interface_from_file(consumer_path)
    provider = extract_interface_from_file(provider_path)
    return compute_alignment(consumer, provider)


def format_alignment_heatmap(
    consumer_name: str,
    provider_name: str,
    score: AlignmentScore,
) -> str:
    """Format alignment score as a heatmap visualization."""
    bar_width = 24

    def bar(value: float) -> str:
        filled = int(value * bar_width)
        empty = bar_width - filled
        return "█" * filled + "░" * empty

    lines: list[str] = []
    lines.append(f"Interface Alignment: {consumer_name} → {provider_name}")
    lines.append("  ┌──────────────────────────────────────────────┐")
    lines.append(f"  │  {bar(score.name_match)}  A_name   = {score.name_match:.2f}   │")
    lines.append(f"  │  {bar(score.signature_match)}  A_sig    = {score.signature_match:.2f}   │")
    lines.append(f"  │  {bar(score.semantic_match)}  A_sem    = {score.semantic_match:.2f}   │")
    lines.append("  │  ─────────────────────────────────────────── │")
    lines.append(f"  │  Combined Alignment A = {score.composite:.2f}                 │")
    lines.append(f"  │  Status: {score.status}                            │")
    lines.append("  └──────────────────────────────────────────────┘")

    return "\n".join(lines)
