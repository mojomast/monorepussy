"""Error classification — distinguish bugs from features in variants."""

from __future__ import annotations

import re
from typing import Optional

from .models import (
    Classification,
    CollationResult,
    Reading,
    VariationUnit,
)


# Known scribal error patterns in code
SCRIBAL_ERROR_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern_description, regex_majority, regex_minority)
    ("off-by-one: > vs >=", r">\s*0", r">=\s*0"),
    ("off-by-one: < vs <=", r"<\s*0", r"<=\s*0"),
    ("off-by-one: > vs >=", r">=\s*1", r">\s*0"),
    ("swapped operator: == vs !=", r"==", r"!="),
    ("missing negation", r"not\s+", r""),
    ("dropped else branch", r"else:", r""),
    ("swapped and/or", r"\band\b", r"\bor\b"),
    ("missing increment", r"\+\s*1", r""),
    ("missing decrement", r"-\s*1", r""),
]

# Conscious modification indicators
CONSCIOUS_MODIFICATION_INDICATORS = [
    "different function name with same behavior",
    "different variable name",
    "added parameter",
    "removed feature",
    "different string literal",
    "different constant value",
    "different import path",
    "different logging framework",
]


def lectio_difficilior_score(majority_text: str, minority_text: str) -> float:
    """Score how likely the majority reading is the original based on
    the 'harder reading' principle.

    Returns 0.0-1.0 where higher = more likely majority is original.
    Scribes simplify; more complex = more likely original.
    """
    if not majority_text or not minority_text:
        return 0.5

    score = 0.5  # baseline

    # Complexity heuristics
    majority_complexity = _code_complexity(majority_text)
    minority_complexity = _code_complexity(minority_text)

    if majority_complexity > minority_complexity:
        # Majority is more complex -> more likely original
        score += 0.2
    elif minority_complexity > majority_complexity:
        # Minority is more complex -> maybe original
        score -= 0.2

    # Check for specific scribal error patterns
    for desc, maj_pat, min_pat in SCRIBAL_ERROR_PATTERNS:
        if re.search(maj_pat, majority_text) and re.search(min_pat, minority_text):
            score += 0.25  # Pattern matches known scribal error
            break

    # Length heuristic: shorter minority often = simplification/omission
    if len(minority_text) < len(majority_text) * 0.5:
        score += 0.1  # Likely omission

    return min(max(score, 0.0), 1.0)


def _code_complexity(text: str) -> float:
    """Heuristic complexity score for a code line."""
    score = 0.0
    score += text.count("(") * 0.5
    score += text.count("[") * 0.5
    score += len(text) * 0.01
    score += text.count("if ") * 1.0
    score += text.count("for ") * 1.0
    score += text.count("while ") * 1.0
    score += text.count("not ") * 0.5
    score += text.count(" and ") * 0.3
    score += text.count(" or ") * 0.3
    return score


def consistency_score(majority_text: str, minority_text: str) -> float:
    """Score whether the variant maintains semantic behavior.

    Returns 0.0-1.0 where higher = more likely same semantics (conscious rename).
    """
    if not majority_text or not minority_text:
        return 0.3

    # Tokenize
    maj_tokens = set(majority_text.split())
    min_tokens = set(minority_text.split())

    if not maj_tokens or not min_tokens:
        return 0.3

    # High overlap suggests rename/structural change
    overlap = maj_tokens & min_tokens
    union = maj_tokens | min_tokens
    jaccard = len(overlap) / len(union) if union else 0.0

    if jaccard >= 0.5:
        return 0.8  # High overlap -> likely conscious rename
    elif jaccard >= 0.3:
        return 0.5
    else:
        return 0.2


def is_scribal_error_pattern(majority_text: str, minority_text: str) -> Optional[str]:
    """Check if the change matches a known scribal error pattern.

    Returns pattern description if matched, None otherwise.
    """
    for desc, maj_pat, min_pat in SCRIBAL_ERROR_PATTERNS:
        if re.search(maj_pat, majority_text) and re.search(min_pat, minority_text):
            return desc
    return None


def classify_variant(unit: VariationUnit) -> Classification:
    """Classify a single variation unit."""
    if not unit.is_variant:
        return Classification.CONSCIOUS_MODIFICATION  # shouldn't happen

    majority = unit.majority_reading
    if majority is None:
        return Classification.AMBIGUOUS

    for minority in unit.minority_readings:
        # Check for known scribal error patterns
        pattern = is_scribal_error_pattern(majority.text, minority.text)
        if pattern:
            return Classification.SCRIBAL_ERROR

        # Check if minority is an omission (absent)
        if minority.text == "(absent)":
            # Omission is often scribal (forgot to copy) but can be intentional
            ld_score = lectio_difficilior_score(majority.text, minority.text)
            if ld_score > 0.6:
                return Classification.SCRIBAL_ERROR
            else:
                return Classification.AMBIGUOUS

        # Lectio difficilior check
        ld_score = lectio_difficilior_score(majority.text, minority.text)

        # Consistency check
        cons_score = consistency_score(majority.text, minority.text)

        # Decision logic
        if ld_score > 0.7 and cons_score < 0.5:
            return Classification.SCRIBAL_ERROR
        elif cons_score > 0.7:
            return Classification.CONSCIOUS_MODIFICATION
        elif ld_score > 0.6:
            return Classification.SCRIBAL_ERROR
        elif cons_score > 0.5:
            return Classification.CONSCIOUS_MODIFICATION
        else:
            return Classification.AMBIGUOUS

    return Classification.AMBIGUOUS


def compute_confidence(unit: VariationUnit, classification: Classification) -> float:
    """Compute confidence score for a classification (0.0-1.0)."""
    if not unit.is_variant:
        return 1.0

    majority = unit.majority_reading
    if majority is None:
        return 0.3

    for minority in unit.minority_readings:
        ld_score = lectio_difficilior_score(majority.text, minority.text)
        cons_score = consistency_score(majority.text, minority.text)

        if classification == Classification.SCRIBAL_ERROR:
            # Confidence based on pattern match and lectio difficilior
            pattern = is_scribal_error_pattern(majority.text, minority.text)
            if pattern:
                return min(0.85 + ld_score * 0.1, 0.95)
            return min(ld_score * 0.9, 0.9)

        elif classification == Classification.CONSCIOUS_MODIFICATION:
            return min(cons_score * 0.95, 0.95)

        else:  # AMBIGUOUS
            return 0.3 + abs(ld_score - cons_score) * 0.2

    return 0.5


def classify_all(collation: CollationResult) -> CollationResult:
    """Classify all variation units in a collation result."""
    for unit in collation.variation_units:
        if unit.is_variant:
            classification = classify_variant(unit)
            unit.classification = classification
            unit.confidence = compute_confidence(unit, classification)

            # Generate rationale
            majority = unit.majority_reading
            if majority:
                for minority in unit.minority_readings:
                    pattern = is_scribal_error_pattern(majority.text, minority.text)
                    if pattern:
                        unit.rationale = f"Matches known scribal error pattern: {pattern}"
                    elif minority.text == "(absent)":
                        unit.rationale = "Omission in minority witnesses"
                    elif classification == Classification.CONSCIOUS_MODIFICATION:
                        unit.rationale = "Conscious modification — different naming or structure"
                    elif classification == Classification.AMBIGUOUS:
                        unit.rationale = "Insufficient evidence to classify definitively"

    return collation
