"""Sheldon grading system for package versions.

Grades packages on a 1-70 scale (the Sheldon numismatic scale) using
four criteria: strike quality, surface preservation, luster, and eye appeal.
Uses harmonic mean to penalize weakness in any single criterion.
"""

from __future__ import annotations

from mint.models import PackageInfo, get_grade_label, get_grade_category


def sheldon_grade(strike: float, surface: float, luster: float, eye_appeal: float) -> int:
    """Compute a Sheldon grade (1-70) from four criteria scores.

    Each input is 0.0-1.0. Uses harmonic mean to penalize weakness
    in any criterion — a coin can't be MS-65 if it has Poor eye appeal.

    Args:
        strike: Build integrity / reproducibility score (0.0-1.0)
        surface: API surface maintenance score (0.0-1.0)
        luster: Documentation quality score (0.0-1.0)
        eye_appeal: Developer experience score (0.0-1.0)

    Returns:
        Sheldon grade from 1 (Poor) to 70 (Mint State Perfect)
    """
    # Clamp inputs to valid range
    strike = max(0.001, min(1.0, strike))
    surface = max(0.001, min(1.0, surface))
    luster = max(0.001, min(1.0, luster))
    eye_appeal = max(0.001, min(1.0, eye_appeal))

    # Harmonic mean — penalizes any single low score
    composite = 4.0 / (1.0 / strike + 1.0 / surface + 1.0 / luster + 1.0 / eye_appeal)
    grade = max(1, min(70, round(composite * 70)))
    return grade


def grade_package(pkg: PackageInfo) -> PackageInfo:
    """Grade a package and populate its Sheldon grade and label.

    Mutates and returns the PackageInfo with sheldon_grade and grade_label set.
    """
    grade = sheldon_grade(
        pkg.strike_quality,
        pkg.surface_preservation,
        pkg.luster,
        pkg.eye_appeal,
    )
    pkg.sheldon_grade = grade
    short_label, category = get_grade_label(grade)
    pkg.grade_label = f"{short_label} ({category})"
    return pkg


def grade_breakdown(strike: float, surface: float, luster: float, eye_appeal: float) -> dict:
    """Return a detailed grade breakdown for the four criteria.

    Each criterion is mapped from 0.0-1.0 to a 1-70 sub-grade and
    combined into the final Sheldon grade.
    """
    s_grade = sheldon_grade(strike, surface, luster, eye_appeal)
    short_label, category = get_grade_label(s_grade)

    return {
        "grade": s_grade,
        "label": short_label,
        "category": category,
        "strike_70": max(1, min(70, round(strike * 70))),
        "surface_70": max(1, min(70, round(surface * 70))),
        "luster_70": max(1, min(70, round(luster * 70))),
        "eye_appeal_70": max(1, min(70, round(eye_appeal * 70))),
    }


def compute_strike_quality(
    reproducible_build: bool = True,
    api_surface_match: float = 1.0,
    type_coverage: float = 0.5,
) -> float:
    """Compute strike quality score from build integrity metrics.

    Args:
        reproducible_build: Whether the build is reproducible
        api_surface_match: Fraction of declared API that matches implementation (0.0-1.0)
        type_coverage: Type definition coverage (0.0-1.0)

    Returns:
        Strike quality score (0.0-1.0)
    """
    repro_score = 1.0 if reproducible_build else 0.3
    score = (repro_score * 0.4 + api_surface_match * 0.35 + type_coverage * 0.25)
    return max(0.0, min(1.0, score))


def compute_surface_preservation(
    deprecated_ratio: float = 0.0,
    avg_issue_age_days: float = 30.0,
    pr_merge_latency_days: float = 7.0,
    changelog_completeness: float = 0.8,
) -> float:
    """Compute surface preservation score from API maintenance metrics.

    Args:
        deprecated_ratio: Fraction of API that is deprecated (0.0-1.0, lower is better)
        avg_issue_age_days: Average age of open issues in days (lower is better)
        pr_merge_latency_days: Average PR merge latency in days (lower is better)
        changelog_completeness: How complete is the changelog (0.0-1.0)

    Returns:
        Surface preservation score (0.0-1.0)
    """
    deprecation_score = 1.0 - min(1.0, deprecated_ratio * 3.0)
    issue_score = max(0.0, 1.0 - avg_issue_age_days / 365.0)
    merge_score = max(0.0, 1.0 - pr_merge_latency_days / 90.0)
    score = (deprecation_score * 0.3 + issue_score * 0.25 + merge_score * 0.2 + changelog_completeness * 0.25)
    return max(0.0, min(1.0, score))


def compute_luster(
    doc_freshness: float = 0.7,
    type_def_coverage: float = 0.5,
    example_completeness: float = 0.6,
    readme_quality: float = 0.7,
) -> float:
    """Compute luster score from documentation quality metrics.

    Args:
        doc_freshness: How up-to-date the docs are (0.0-1.0)
        type_def_coverage: Type definition coverage (0.0-1.0)
        example_completeness: Completeness of usage examples (0.0-1.0)
        readme_quality: README quality score (0.0-1.0)

    Returns:
        Luster score (0.0-1.0)
    """
    score = (doc_freshness * 0.3 + type_def_coverage * 0.25 + example_completeness * 0.2 + readme_quality * 0.25)
    return max(0.0, min(1.0, score))


def compute_eye_appeal(
    install_size_efficiency: float = 0.7,
    startup_time: float = 0.8,
    import_clarity: float = 0.8,
    error_message_quality: float = 0.6,
) -> float:
    """Compute eye appeal score from developer experience metrics.

    Args:
        install_size_efficiency: How lean the package is (0.0-1.0)
        startup_time: How fast it starts (0.0-1.0)
        import_clarity: How clean the import API is (0.0-1.0)
        error_message_quality: Quality of error messages (0.0-1.0)

    Returns:
        Eye appeal score (0.0-1.0)
    """
    score = (install_size_efficiency * 0.25 + startup_time * 0.25 + import_clarity * 0.25 + error_message_quality * 0.25)
    return max(0.0, min(1.0, score))
