"""Glass Type Classifier — Test Fragility Taxonomy."""

from __future__ import annotations

from typing import Dict, Optional

from ussy_calibre.models import (
    CTEProfile,
    GlassClassification,
    GlassType,
    ShockResistance,
    TemperResult,
)


def classify_glass_type(
    cte: float,
    shock_resistance: float,
    brittleness: float,
) -> GlassType:
    """Classify a test into a glass type based on measured properties.

    Glass Type        | CTE      | Shock Resistance | Brittleness
    ------------------|----------|------------------|------------
    Fused Silica      | Very Low | Very High        | ~0
    Borosilicate      | Low      | High             | <0.1
    Soda-Lime         | Medium   | Medium           | 0.1-0.3
    Lead Crystal      | High     | Low              | 0.3-0.6
    Tempered Soda-Lime| Medium   | Medium (apparent)| >0.6
    """
    # Tempered soda-lime: high brittleness overrides everything
    if brittleness > 0.6:
        return GlassType.TEMPERED_SODA_LIME

    # Lead crystal: high CTE or low shock resistance with significant brittleness
    if cte > 0.4 or (shock_resistance < 0.3 and brittleness > 0.3):
        return GlassType.LEAD_CRYSTAL

    # Soda-lime: medium properties
    if cte > 0.15 or brittleness > 0.1:
        return GlassType.SODA_LIME

    # Borosilicate: low CTE, reasonable shock resistance
    if cte > 0.05 or brittleness > 0.01:
        return GlassType.BOROSILICATE

    # Fused silica: nearly zero CTE and brittleness, very high shock resistance
    return GlassType.FUSED_SILICA


def compute_classification_confidence(
    glass_type: GlassType,
    cte: float,
    shock_resistance: float,
    brittleness: float,
) -> float:
    """Compute confidence in the glass type classification.

    Higher confidence when properties clearly fall within the type's range.
    """
    confidence = 0.5  # base confidence

    if glass_type == GlassType.FUSED_SILICA:
        if cte < 0.02:
            confidence += 0.2
        if brittleness < 0.01:
            confidence += 0.2
        if shock_resistance > 0.8:
            confidence += 0.1
    elif glass_type == GlassType.BOROSILICATE:
        if 0.05 <= cte <= 0.15:
            confidence += 0.2
        if brittleness < 0.1:
            confidence += 0.2
        if shock_resistance > 0.5:
            confidence += 0.1
    elif glass_type == GlassType.SODA_LIME:
        if 0.15 <= cte <= 0.4:
            confidence += 0.2
        if 0.1 <= brittleness <= 0.3:
            confidence += 0.2
    elif glass_type == GlassType.LEAD_CRYSTAL:
        if cte > 0.4:
            confidence += 0.2
        if brittleness > 0.3:
            confidence += 0.2
    elif glass_type == GlassType.TEMPERED_SODA_LIME:
        if brittleness > 0.6:
            confidence += 0.3
        if cte < 0.4:
            confidence += 0.1  # "medium" CTE confirms tempered soda-lime

    return min(confidence, 1.0)


def classify_tests(
    cte_profiles: Dict[str, CTEProfile],
    shock_resistances: Dict[str, ShockResistance],
    temper_results: Dict[str, TemperResult],
) -> Dict[str, GlassClassification]:
    """Classify all tests into glass types.

    Uses CTE profile, shock resistance, and brittleness index to
    assign each test a glass type with confidence score.
    """
    classifications: Dict[str, GlassClassification] = {}

    all_tests = set(cte_profiles.keys()) | set(shock_resistances.keys()) | set(temper_results.keys())

    for test_name in all_tests:
        cte_profile = cte_profiles.get(test_name)
        shock_res = shock_resistances.get(test_name)
        temper = temper_results.get(test_name)

        cte = cte_profile.composite_cte if cte_profile else 0.1
        shock = shock_res.resistance_score if shock_res else 0.5
        brit = temper.brittleness_index if temper else 0.0

        glass_type = classify_glass_type(cte, shock, brit)
        confidence = compute_classification_confidence(glass_type, cte, shock, brit)

        classifications[test_name] = GlassClassification(
            test_name=test_name,
            glass_type=glass_type,
            cte=cte,
            shock_resistance=shock,
            brittleness=brit,
            confidence=confidence,
        )

    return classifications


def format_classifications(classifications: Dict[str, GlassClassification]) -> str:
    """Format glass type classifications."""
    lines = []
    lines.append("=" * 60)
    lines.append("GLASS TYPE CLASSIFIER — Test Fragility Taxonomy")
    lines.append("=" * 60)
    lines.append("")

    if not classifications:
        lines.append("No test results to classify.")
        return "\n".join(lines)

    # Sort by glass type severity (most fragile first)
    severity_order = {
        GlassType.TEMPERED_SODA_LIME: 0,
        GlassType.LEAD_CRYSTAL: 1,
        GlassType.SODA_LIME: 2,
        GlassType.BOROSILICATE: 3,
        GlassType.FUSED_SILICA: 4,
    }

    sorted_cls = sorted(
        classifications.values(),
        key=lambda c: (severity_order.get(c.glass_type, 5), -c.brittleness),
    )

    for cls in sorted_cls:
        icon = {
            GlassType.FUSED_SILICA: "💎",
            GlassType.BOROSILICATE: "🔬",
            GlassType.SODA_LIME: "🪟",
            GlassType.LEAD_CRYSTAL: "🍷",
            GlassType.TEMPERED_SODA_LIME: "⚡",
        }
        lines.append(f"  {icon.get(cls.glass_type, '?')} {cls.test_name}")
        lines.append(f"    Type: {cls.glass_type.label} (confidence: {cls.confidence:.0%})")
        lines.append(f"    CTE: {cls.cte:.4f}  Shock R: {cls.shock_resistance:.4f}  Brittleness: {cls.brittleness:.4f}")
        lines.append(f"    → {cls.recommendation}")
        lines.append("")

    # Distribution
    dist: Dict[str, int] = {}
    for cls in classifications.values():
        key = cls.glass_type.label
        dist[key] = dist.get(key, 0) + 1

    lines.append("Glass Distribution:")
    for gtype in [GlassType.FUSED_SILICA, GlassType.BOROSILICATE,
                  GlassType.SODA_LIME, GlassType.LEAD_CRYSTAL,
                  GlassType.TEMPERED_SODA_LIME]:
        count = dist.get(gtype.label, 0)
        if count > 0:
            pct = count / len(classifications) * 100
            bar = "█" * int(pct / 2)
            lines.append(f"  {gtype.label:20s} {count:3d} ({pct:5.1f}%) {bar}")

    return "\n".join(lines)
