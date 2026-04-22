"""Tests for the classify module."""

from ussy_stemma.classify import (
    classify_all,
    classify_variant,
    compute_confidence,
    consistency_score,
    is_scribal_error_pattern,
    lectio_difficilior_score,
)
from ussy_stemma.collation import collate
from ussy_stemma.models import (
    Classification,
    CollationResult,
    Reading,
    VariantType,
    VariationUnit,
    Witness,
)


class TestLectioDifficiliorScore:
    def test_more_complex_majority(self):
        # Majority is more complex -> higher score
        score = lectio_difficilior_score(
            "if charge > 0 and check_valid(charge):",
            "if charge >= 0:",
        )
        assert score > 0.5

    def test_simpler_majority(self):
        # Majority is simpler -> lower score
        score = lectio_difficilior_score(
            "if x > 0:",
            "if x > 0 and y > 0 and z > 0:",
        )
        assert score < 0.7

    def test_empty_texts(self):
        score = lectio_difficilior_score("", "")
        assert score == 0.5

    def test_one_empty(self):
        score = lectio_difficilior_score("x = 1", "")
        assert score == 0.5


class TestConsistencyScore:
    def test_high_overlap(self):
        score = consistency_score("charge = calc(order)", "charge = compute(order)")
        assert score > 0.5

    def test_low_overlap(self):
        score = consistency_score("if charge > 0:", "return None")
        assert score < 0.5

    def test_empty(self):
        score = consistency_score("", "x = 1")
        assert score < 0.5


class TestIsScribalErrorPattern:
    def test_off_by_one_gt_gte(self):
        result = is_scribal_error_pattern("if charge > 0:", "if charge >= 0:")
        assert result is not None
        assert "off-by-one" in result.lower()

    def test_not_scribal_error(self):
        result = is_scribal_error_pattern("charge = calc(order)", "charge = compute(order)")
        assert result is None

    def test_swapped_operator(self):
        result = is_scribal_error_pattern("if x == y:", "if x != y:")
        assert result is not None


class TestClassifyVariant:
    def test_scribal_error_classification(self):
        r1 = Reading(text="if charge > 0:", witnesses=["A", "B", "C"], variant_type=VariantType.MAJORITY)
        r2 = Reading(text="if charge >= 0:", witnesses=["D", "E"], variant_type=VariantType.VARIANT)
        unit = VariationUnit(line_number=5, readings=[r1, r2])
        result = classify_variant(unit)
        assert result == Classification.SCRIBAL_ERROR

    def test_conscious_modification(self):
        r1 = Reading(text="charge = calc(order)", witnesses=["A", "B"], variant_type=VariantType.MAJORITY)
        r2 = Reading(text="charge = compute(order)", witnesses=["C", "E"], variant_type=VariantType.VARIANT)
        unit = VariationUnit(line_number=4, readings=[r1, r2])
        result = classify_variant(unit)
        assert result == Classification.CONSCIOUS_MODIFICATION

    def test_omission_ambiguous(self):
        r1 = Reading(text="log.info(f\"Processed\")", witnesses=["A", "B"], variant_type=VariantType.MAJORITY)
        r2 = Reading(text="(absent)", witnesses=["C", "E"], variant_type=VariantType.OMISSION)
        unit = VariationUnit(line_number=8, readings=[r1, r2])
        result = classify_variant(unit)
        # Omission could be scribal or conscious
        assert result in (Classification.SCRIBAL_ERROR, Classification.AMBIGUOUS, Classification.CONSCIOUS_MODIFICATION)


class TestComputeConfidence:
    def test_high_confidence_scribal(self):
        r1 = Reading(text="if charge > 0:", witnesses=["A", "B", "C"])
        r2 = Reading(text="if charge >= 0:", witnesses=["D", "E"])
        unit = VariationUnit(line_number=5, readings=[r1, r2])
        conf = compute_confidence(unit, Classification.SCRIBAL_ERROR)
        assert conf > 0.5

    def test_confidence_range(self):
        r1 = Reading(text="x = 1", witnesses=["A", "B"])
        r2 = Reading(text="x = 2", witnesses=["C"])
        unit = VariationUnit(line_number=1, readings=[r1, r2])
        conf = compute_confidence(unit, Classification.AMBIGUOUS)
        assert 0.0 <= conf <= 1.0


class TestClassifyAll:
    def test_classify_payment_witnesses(self, all_witnesses):
        collation = collate(all_witnesses)
        result = classify_all(collation)
        variant_units = [v for v in result.variation_units if v.is_variant]
        # Should have some classified variants
        classified = [v for v in variant_units if v.classification is not None]
        assert len(classified) > 0

    def test_confidence_scores_set(self, all_witnesses):
        collation = collate(all_witnesses)
        result = classify_all(collation)
        for v in result.variation_units:
            if v.is_variant:
                assert v.confidence >= 0.0
