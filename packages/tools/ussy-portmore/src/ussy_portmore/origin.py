"""Rules of Origin — Provenance & Dedication Determination."""
from __future__ import annotations

from ussy_portmore.models import OriginDetermination, OriginStatus


def wholly_obtained_test(
    third_party_ratio: float,
    deminimis_threshold: float = 0.05,
) -> bool:
    """Determine if a module is wholly obtained (no foreign obligations).

    If non-originating code is below de minimis threshold, it doesn't affect
    the module's origin classification.
    """
    return third_party_ratio <= deminimis_threshold


def substantial_transformation_ctc(
    original_hs_code: str,
    modified_hs_code: str,
) -> bool:
    """Change in Tariff Classification test.

    If modification changes the license classification (e.g., MIT → GPL fork),
    then the NEW license governs as a 'new originating product'.
    """
    return original_hs_code != modified_hs_code


def value_added_test(
    modification_ratio: float,
    threshold: float = 0.40,
) -> bool:
    """Value-Added Test.

    If modifications constitute >= threshold of the module (default 40%),
    then the module is 'substantially transformed'.
    V_mod / V_total >= theta_transform
    """
    return modification_ratio >= threshold


def de_minimis_test(
    third_party_ratio: float,
    deminimis_threshold: float = 0.05,
) -> bool:
    """De Minimis test.

    If non-originating (third-party) code constitutes < 5% of a module,
    it doesn't affect the module's origin classification.
    """
    return third_party_ratio < deminimis_threshold


def accumulation_test(
    contributor_ratios: list[float],
    threshold: float = 0.40,
) -> bool:
    """Accumulation test.

    Modifications by multiple contributors in the same 'trade zone'
    (same organization or CLA signatories) can be accumulated
    toward the substantial transformation threshold.
    """
    total = sum(contributor_ratios)
    return total >= threshold


def absorption_rule(
    component_origin: OriginStatus,
    aggregate_origin: OriginStatus,
) -> bool:
    """Absorption rule.

    An 'originating' component retains its origin status even when
    incorporated into a larger non-originating product.
    """
    return component_origin == OriginStatus.WHOLLY_OBTAINED


def determine_origin(
    module: str,
    third_party_ratio: float,
    modification_ratio: float,
    original_hs_code: str,
    modified_hs_code: str,
    contributor_ratios: list[float] | None = None,
    threshold: float = 0.40,
    deminimis_threshold: float = 0.05,
) -> OriginDetermination:
    """Perform full origin determination for a module.

    Applies tests in sequence:
    1. Wholly obtained test
    2. Substantial transformation (CTC)
    3. Value-added test
    4. De minimis
    5. Accumulation (if applicable)
    6. Absorption (if applicable)
    """
    # Step 1: Wholly obtained?
    is_wholly_obtained = wholly_obtained_test(third_party_ratio, deminimis_threshold)
    if is_wholly_obtained:
        return OriginDetermination(
            module=module,
            status=OriginStatus.WHOLLY_OBTAINED,
            wholly_obtained=True,
            ct_classification_changed=False,
            value_added_ratio=modification_ratio,
            de_minimis_ratio=third_party_ratio,
            accumulation_applied=False,
            absorption_applied=False,
            threshold=threshold,
            deminimis_threshold=deminimis_threshold,
        )

    # Step 2: CTC (Change in Tariff Classification)
    ct_changed = substantial_transformation_ctc(original_hs_code, modified_hs_code)

    # Step 3: Value-added test
    value_added = value_added_test(modification_ratio, threshold)

    # Step 4: De minimis
    is_deminimis = de_minimis_test(third_party_ratio, deminimis_threshold)

    # Step 5: Accumulation
    acc_applied = False
    if contributor_ratios and not value_added:
        acc_applied = accumulation_test(contributor_ratios, threshold)
        if acc_applied:
            value_added = True

    # Step 6: Absorption
    abs_applied = False  # Would need component-level data

    # Determine final status
    if ct_changed or value_added:
        status = OriginStatus.SUBSTANTIALLY_TRANSFORMED
    else:
        status = OriginStatus.NON_ORIGINATING

    return OriginDetermination(
        module=module,
        status=status,
        wholly_obtained=is_wholly_obtained,
        ct_classification_changed=ct_changed,
        value_added_ratio=modification_ratio,
        de_minimis_ratio=third_party_ratio,
        accumulation_applied=acc_applied,
        absorption_applied=abs_applied,
        threshold=threshold,
        deminimis_threshold=deminimis_threshold,
    )
