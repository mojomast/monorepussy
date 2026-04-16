"""Composition and fineness analysis for packages.

Computes the dependency alloy composition, fineness (purity ratio),
and categorizes transitive dependencies by function.
"""

from __future__ import annotations

from mint.models import Composition


def compute_fineness(own_loc: int, vendored_loc: int = 0, bundled_loc: int = 0) -> float:
    """Compute fineness (purity ratio) of a package.

    Analogous to silver fineness in millesimal units:
        fineness = own_loc / (own_loc + vendored_loc + bundled_loc)

    A package with fineness=0.999 is pure — all its own code.
    A package with fineness=0.250 is debased — 75% from others.

    Args:
        own_loc: Lines of code written by the package itself
        vendored_loc: Lines of vendored (copied-in) code
        bundled_loc: Lines of bundled (packed-in) code

    Returns:
        Fineness ratio (0.0 to 1.0). Returns 1.0 if total is 0.
    """
    total = own_loc + vendored_loc + bundled_loc
    if total == 0:
        return 1.0
    return own_loc / total


def categorize_alloy(dependencies: list[dict]) -> dict[str, int]:
    """Categorize transitive dependencies by function (alloy breakdown).

    Categories:
    - core: Direct functional dependencies
    - build: Build-time only dependencies
    - test: Test-only dependencies
    - filler: Dependencies that could be replaced
    - contaminant: Dependencies introducing risk

    Args:
        dependencies: List of dependency dicts with keys: name, category

    Returns:
        Dict mapping category name to count.
    """
    breakdown = {"core": 0, "build": 0, "test": 0, "filler": 0, "contaminant": 0}
    for dep in dependencies:
        cat = dep.get("category", "core")
        if cat in breakdown:
            breakdown[cat] += 1
        else:
            breakdown["filler"] += 1
    return breakdown


def compute_maintainer_overlap(maintainers_per_pkg: dict[str, list[str]]) -> float:
    """Compute fraction of packages sharing at least one maintainer.

    Args:
        maintainers_per_pkg: Mapping of package name to list of maintainer names

    Returns:
        Overlap ratio (0.0 = no overlap, 1.0 = all share maintainers)
    """
    packages = list(maintainers_per_pkg.keys())
    if len(packages) < 2:
        return 0.0

    overlapping_pairs = 0
    total_pairs = 0

    for i in range(len(packages)):
        for j in range(i + 1, len(packages)):
            total_pairs += 1
            set_a = set(maintainers_per_pkg[packages[i]])
            set_b = set(maintainers_per_pkg[packages[j]])
            if set_a & set_b:
                overlapping_pairs += 1

    if total_pairs == 0:
        return 0.0
    return overlapping_pairs / total_pairs


def analyze_license_mix(licenses: list[str]) -> dict[str, int]:
    """Compute license composition of transitive dependency tree.

    Args:
        licenses: List of license identifiers from transitive deps

    Returns:
        Dict mapping license type to count.
    """
    mix: dict[str, int] = {}
    for lic in licenses:
        normalized = lic.strip() if lic else "UNKNOWN"
        mix[normalized] = mix.get(normalized, 0) + 1
    return mix


def compute_composition(
    own_loc: int = 1000,
    vendored_loc: int = 0,
    bundled_loc: int = 0,
    dependencies: list | None = None,
    maintainers_per_pkg: dict | None = None,
    licenses: list | None = None,
    transitive_depth: int = 0,
) -> Composition:
    """Compute full composition analysis for a package.

    Args:
        own_loc: Lines of own code
        vendored_loc: Lines of vendored code
        bundled_loc: Lines of bundled code
        dependencies: List of dependency dicts with category field
        maintainers_per_pkg: Mapping of pkg name to maintainer list
        licenses: List of license identifiers
        transitive_depth: Depth of transitive dependency tree

    Returns:
        Composition dataclass with all computed values
    """
    if dependencies is None:
        dependencies = []
    if maintainers_per_pkg is None:
        maintainers_per_pkg = {}
    if licenses is None:
        licenses = []

    own_code_ratio = compute_fineness(own_loc, vendored_loc, bundled_loc)
    alloy_breakdown = categorize_alloy(dependencies)
    maintainer_overlap = compute_maintainer_overlap(maintainers_per_pkg)
    license_mix = analyze_license_mix(licenses)
    transitive_count = len(dependencies)

    return Composition(
        own_code_ratio=own_code_ratio,
        transitive_depth=transitive_depth,
        transitive_count=transitive_count,
        alloy_breakdown=alloy_breakdown,
        maintainer_overlap=maintainer_overlap,
        license_mix=license_mix,
    )
