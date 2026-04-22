"""Tests for Customs Valuation — Compliance Cost Assessment."""
import pytest

from ussy_portmore.valuation import (
    article8_adjustments,
    compute_valuation_hierarchy,
    method1_transaction_value,
    method2_identical_goods,
    method3_similar_goods,
    method4_deductive,
    method5_computed,
    method6_fallback,
    related_party_test,
)
from ussy_portmore.models import ValuationMethod


class TestMethod1TransactionValue:
    """Tests for Method 1 — Transaction Value."""

    def test_mit_low_cost(self):
        result = method1_transaction_value("MIT")
        assert result.value > 0
        assert result.value < 1000  # MIT has minimal obligations

    def test_gpl3_high_cost(self):
        result = method1_transaction_value("GPL-3.0")
        assert result.value > 1000  # GPL has significant obligations

    def test_cc0_zero_cost(self):
        result = method1_transaction_value("CC0-1.0")
        assert result.value == 0.0  # No obligations

    def test_obligations_populated(self):
        result = method1_transaction_value("Apache-2.0")
        assert len(result.obligations) > 0

    def test_method_enum(self):
        result = method1_transaction_value("MIT")
        assert result.method == ValuationMethod.TRANSACTION


class TestMethod2IdenticalGoods:
    """Tests for Method 2 — Identical Goods."""

    def test_with_similar_projects(self):
        result = method2_identical_goods("MIT", [200.0, 300.0, 250.0])
        assert result.value == pytest.approx(250.0)

    def test_without_similar_projects(self):
        m1 = method1_transaction_value("MIT")
        result = method2_identical_goods("MIT")
        # Should use 1.05x of method 1 as fallback
        assert result.value == pytest.approx(m1.value * 1.05)

    def test_method_enum(self):
        result = method2_identical_goods("MIT")
        assert result.method == ValuationMethod.IDENTICAL


class TestMethod3SimilarGoods:
    """Tests for Method 3 — Similar Goods."""

    def test_permissive_multiplier(self):
        m1 = method1_transaction_value("MIT")
        result = method3_similar_goods("MIT")
        assert result.value == pytest.approx(m1.value * 1.0)

    def test_copyleft_higher_multiplier(self):
        m1 = method1_transaction_value("GPL-3.0")
        result = method3_similar_goods("GPL-3.0")
        assert result.value > m1.value  # 1.5x multiplier

    def test_method_enum(self):
        result = method3_similar_goods("MIT")
        assert result.method == ValuationMethod.SIMILAR


class TestMethod4Deductive:
    """Tests for Method 4 — Deductive Value."""

    def test_with_explicit_fraction(self):
        result = method4_deductive(100000.0, obligation_fraction=0.10)
        assert result.value == pytest.approx(10000.0)

    def test_with_license_based_fraction(self):
        result = method4_deductive(100000.0, license_id="GPL-3.0")
        assert result.value > 0
        # GPL-3.0 has ~40% fraction
        assert result.value == pytest.approx(40000.0)

    def test_permissive_low_fraction(self):
        result = method4_deductive(100000.0, license_id="MIT")
        assert result.value == pytest.approx(2000.0)  # 2% fraction

    def test_zero_project_value(self):
        result = method4_deductive(0.0, obligation_fraction=0.10)
        assert result.value == 0.0

    def test_method_enum(self):
        result = method4_deductive(100000.0, obligation_fraction=0.10)
        assert result.method == ValuationMethod.DEDUCTIVE


class TestMethod5Computed:
    """Tests for Method 5 — Computed Value."""

    def test_with_explicit_costs(self):
        result = method5_computed(50000.0, compliance_overhead=5000.0, risk_multiplier=1.5)
        assert result.value == pytest.approx(82500.0)

    def test_with_license_overhead(self):
        result = method5_computed(50000.0, license_id="GPL-3.0")
        assert result.value > 50000.0

    def test_method_enum(self):
        result = method5_computed(50000.0, compliance_overhead=5000.0)
        assert result.method == ValuationMethod.COMPUTED


class TestMethod6Fallback:
    """Tests for Method 6 — Fall-back."""

    def test_upper_bound(self):
        results = [
            method1_transaction_value("MIT"),
            method3_similar_goods("MIT"),
        ]
        result = method6_fallback(results, upper_bound=True)
        assert result.value == min(r.value for r in results)

    def test_lower_bound(self):
        results = [
            method1_transaction_value("MIT"),
            method3_similar_goods("MIT"),
        ]
        result = method6_fallback(results, upper_bound=False)
        assert result.value == max(r.value for r in results)

    def test_empty_results(self):
        result = method6_fallback([], upper_bound=True)
        assert result.value == 0.0

    def test_method_enum(self):
        results = [method1_transaction_value("MIT")]
        result = method6_fallback(results)
        assert result.method == ValuationMethod.FALLBACK


class TestArticle8Adjustments:
    """Tests for Article 8 adjustments."""

    def test_no_adjustments(self):
        assert article8_adjustments() == 0.0

    def test_royalties_only(self):
        assert article8_adjustments(royalties=1000.0) == 1000.0

    def test_all_adjustments(self):
        total = article8_adjustments(royalties=1000.0, assists=500.0, resale_proceeds=200.0)
        assert total == pytest.approx(1700.0)


class TestRelatedPartyTest:
    """Tests for the related-party test."""

    def test_not_same_org(self):
        assert related_party_test(False, 1000.0) == 0.0

    def test_same_org_arms_length_higher(self):
        adj = related_party_test(True, 1000.0, arms_length_value=1500.0)
        assert adj == pytest.approx(500.0)

    def test_same_org_arms_length_lower(self):
        adj = related_party_test(True, 1000.0, arms_length_value=800.0)
        assert adj == 0.0  # No adjustment needed

    def test_same_org_no_arms_length(self):
        adj = related_party_test(True, 1000.0)
        assert adj == 0.0


class TestValuationHierarchy:
    """Tests for the full 6-method valuation hierarchy."""

    def test_basic_hierarchy(self):
        hierarchy = compute_valuation_hierarchy("MIT")
        assert len(hierarchy.results) >= 4  # At least methods 1-3 + 6
        assert hierarchy.final_value > 0
        assert hierarchy.final_method == ValuationMethod.TRANSACTION

    def test_with_project_value(self):
        hierarchy = compute_valuation_hierarchy(
            "GPL-3.0", project_value=100000.0,
        )
        # Should include deductive method
        methods = [r.method for r in hierarchy.results]
        assert ValuationMethod.DEDUCTIVE in methods

    def test_with_development_cost(self):
        hierarchy = compute_valuation_hierarchy(
            "MIT", development_cost=50000.0,
        )
        methods = [r.method for r in hierarchy.results]
        assert ValuationMethod.COMPUTED in methods

    def test_article8_included(self):
        hierarchy = compute_valuation_hierarchy(
            "MIT", article8={"royalties": 1000.0, "assists": 500.0},
        )
        assert hierarchy.final_value > method1_transaction_value("MIT").value

    def test_related_party_adjustment(self):
        hierarchy = compute_valuation_hierarchy(
            "MIT", is_same_org=True, arms_length_value=50000.0,
        )
        # Adjustment should be applied
        assert hierarchy.final_value >= method1_transaction_value("MIT").value

    def test_cc0_zero_obligations(self):
        hierarchy = compute_valuation_hierarchy("CC0-1.0")
        assert hierarchy.results[0].value == 0.0

    def test_timestamp_populated(self):
        hierarchy = compute_valuation_hierarchy("MIT")
        assert hierarchy.timestamp != ""

    def test_gpl_more_expensive_than_mit(self):
        mit_hierarchy = compute_valuation_hierarchy("MIT")
        gpl_hierarchy = compute_valuation_hierarchy("GPL-3.0")
        assert gpl_hierarchy.final_value > mit_hierarchy.final_value
