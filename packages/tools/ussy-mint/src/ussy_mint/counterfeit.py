"""Counterfeit detection for package supply chain security.

Detects typosquatting, dependency confusion, account takeover,
build injection, and die clash contamination.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ussy_mint.distance import levenshtein_distance, is_typosquat, normalized_distance
from ussy_mint.models import MintMark, ProvenanceLevel


class CounterfeitType(Enum):
    """Types of counterfeit detected."""
    TYPOSQUAT = "typosquat"
    DEPENDENCY_CONFUSION = "dependency_confusion"
    ACCOUNT_TAKEOVER = "account_takeover"
    BUILD_INJECTION = "build_injection"
    DIE_CLASH = "die_clash"
    PROVENANCE_GAP = "provenance_gap"


class Severity(Enum):
    """Severity of a counterfeit finding."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CounterfeitFinding:
    """A single counterfeit detection result."""
    package: str
    version: str = ""
    counterfeit_type: CounterfeitType = CounterfeitType.TYPOSQUAT
    severity: Severity = Severity.WARNING
    confidence: float = 0.0
    description: str = ""
    details: dict = field(default_factory=dict)


def detect_typosquat(
    package_name: str,
    known_packages: list[str],
    max_distance: int = 2,
) -> list[CounterfeitFinding]:
    """Detect if a package name is a typosquat of a known package.

    Uses Levenshtein distance to find similar names.

    Args:
        package_name: The package name to check
        known_packages: List of well-known package names
        max_distance: Maximum edit distance to consider (default 2)

    Returns:
        List of CounterfeitFinding for each potential typosquat
    """
    hits = is_typosquat(package_name, known_packages, max_distance)
    findings = []
    for known_name, distance in hits:
        max_len = max(len(package_name), len(known_name))
        confidence = (1.0 - distance / max_len)
        findings.append(CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.TYPOSQUAT,
            severity=Severity.CRITICAL if distance == 1 else Severity.WARNING,
            confidence=round(confidence, 3),
            description=f'Typosquat of "{known_name}" (Levenshtein distance={distance})',
            details={"similar_to": known_name, "distance": distance},
        ))
    return findings


def detect_dependency_confusion(
    package_name: str,
    private_registries: list[str],
    public_registry: str = "npm",
    current_registry: str = "npm",
) -> Optional[CounterfeitFinding]:
    """Detect dependency confusion attacks.

    A dependency confusion attack occurs when the same package name exists
    on both a private and public registry, and the package manager resolves
    to the public (potentially malicious) version.

    Args:
        package_name: The package name to check
        private_registries: List of private registry names
        public_registry: The expected public registry
        current_registry: Where the package was actually resolved from

    Returns:
        CounterfeitFinding if dependency confusion is detected, None otherwise
    """
    if current_registry != public_registry and current_registry not in private_registries:
        # Package resolved from unexpected registry
        return CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.DEPENDENCY_CONFUSION,
            severity=Severity.CRITICAL,
            confidence=0.9,
            description=f'Package from unexpected registry: {current_registry} (expected {public_registry})',
            details={"expected_registry": public_registry, "actual_registry": current_registry},
        )
    return None


def detect_account_takeover(
    package_name: str,
    current_publisher: str,
    previous_publishers: list[str],
    package_age_days: int = 365,
) -> Optional[CounterfeitFinding]:
    """Detect potential account takeover via publisher changes.

    Flags when a new publisher appears on an established package
    without continuity from previous publishers.

    Args:
        package_name: The package name
        current_publisher: The publisher of the current version
        previous_publishers: List of publishers of previous versions
        package_age_days: How long the package has existed

    Returns:
        CounterfeitFinding if account takeover is suspected, None otherwise
    """
    if not previous_publishers:
        return None

    if current_publisher not in previous_publishers and package_age_days > 90:
        confidence = min(1.0, package_age_days / 365.0) * 0.7
        return CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.ACCOUNT_TAKEOVER,
            severity=Severity.CRITICAL,
            confidence=round(confidence, 3),
            description=f'New publisher "{current_publisher}" on established package (previous: {", ".join(previous_publishers)})',
            details={
                "current_publisher": current_publisher,
                "previous_publishers": previous_publishers,
            },
        )
    return None


def detect_build_injection(
    package_name: str,
    declared_hash: str,
    actual_hash: str,
) -> Optional[CounterfeitFinding]:
    """Detect build injection via artifact hash mismatch.

    When the published artifact hash doesn't match what a reproducible
    build would produce, it indicates supply chain compromise.

    Args:
        package_name: The package name
        declared_hash: The expected/reproducible build hash
        actual_hash: The actual published artifact hash

    Returns:
        CounterfeitFinding if build injection is detected, None otherwise
    """
    if declared_hash and actual_hash and declared_hash != actual_hash:
        return CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.BUILD_INJECTION,
            severity=Severity.CRITICAL,
            confidence=0.95,
            description=f'Artifact hash mismatch: expected {declared_hash[:16]}... got {actual_hash[:16]}...',
            details={"declared_hash": declared_hash, "actual_hash": actual_hash},
        )
    return None


def detect_die_clash(
    package_name: str,
    foreign_files: list[str],
) -> Optional[CounterfeitFinding]:
    """Detect die clash — build contamination from another package.

    A die clash occurs when the build system leaks files from a different
    package into the artifact (e.g., path traversal, workspace leak).

    Args:
        package_name: The package name
        foreign_files: List of files from other packages found in the artifact

    Returns:
        CounterfeitFinding if die clash is detected, None otherwise
    """
    if foreign_files:
        return CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.DIE_CLASH,
            severity=Severity.WARNING,
            confidence=0.7,
            description=f'Contains {len(foreign_files)} file(s) from another package (build contamination)',
            details={"foreign_files": foreign_files[:10]},  # Cap at 10 for display
        )
    return None


def detect_provenance_gap(
    package_name: str,
    provenance_level: ProvenanceLevel,
) -> Optional[CounterfeitFinding]:
    """Detect provenance gaps — packages without verified chain of custody.

    Packages below Level 2 should be flagged as provenance gaps.

    Args:
        package_name: The package name
        provenance_level: The verified provenance level

    Returns:
        CounterfeitFinding if provenance gap is detected, None otherwise
    """
    if provenance_level < ProvenanceLevel.SOURCE_LINKED:
        severity = Severity.WARNING if provenance_level == ProvenanceLevel.BUILD_SIGNED else Severity.INFO
        return CounterfeitFinding(
            package=package_name,
            counterfeit_type=CounterfeitType.PROVENANCE_GAP,
            severity=severity,
            confidence=0.5,
            description=f'Provenance gap: Level {int(provenance_level)} ({provenance_level.name}) — no verified chain of custody',
            details={"provenance_level": int(provenance_level)},
        )
    return None


def compute_counterfeit_confidence(
    package_name: str,
    similar_name: str,
    registry_mismatch: bool = False,
    signature_absent: bool = True,
) -> float:
    """Compute composite counterfeit confidence score.

    confidence = (1 - levenshtein/max_length) * registry_mismatch * signature_absence

    Args:
        package_name: The package name
        similar_name: The name it resembles
        registry_mismatch: Whether the registry differs from expected
        signature_absent: Whether provenance signature is absent

    Returns:
        Confidence score (0.0-1.0). Higher = more likely counterfeit.
    """
    norm_dist = normalized_distance(package_name, similar_name)
    name_score = 1.0 - norm_dist
    reg_factor = 1.5 if registry_mismatch else 1.0
    sig_factor = 1.3 if signature_absent else 1.0
    confidence = name_score * reg_factor * sig_factor
    return max(0.0, min(1.0, confidence))


def authenticate_package(
    package_name: str,
    version: str = "",
    known_packages: list | None = None,
    current_registry: str = "npm",
    expected_registry: str = "npm",
    current_publisher: str = "",
    previous_publishers: list | None = None,
    declared_hash: str = "",
    actual_hash: str = "",
    foreign_files: list | None = None,
    provenance_level: ProvenanceLevel = ProvenanceLevel.UNVERIFIED,
    package_age_days: int = 0,
) -> list[CounterfeitFinding]:
    """Run all counterfeit detection checks on a package.

    Args:
        package_name: Package name to authenticate
        version: Package version
        known_packages: List of well-known package names for typosquat check
        current_registry: Registry where package was resolved
        expected_registry: Expected registry for this package
        current_publisher: Publisher of current version
        previous_publishers: Publishers of previous versions
        declared_hash: Expected reproducible build hash
        actual_hash: Actual published artifact hash
        foreign_files: Files from other packages in the artifact
        provenance_level: Verified provenance level
        package_age_days: Age of the package in days

    Returns:
        List of all CounterfeitFinding results
    """
    if known_packages is None:
        known_packages = []
    if previous_publishers is None:
        previous_publishers = []
    if foreign_files is None:
        foreign_files = []

    findings: list[CounterfeitFinding] = []

    # Typosquatting detection
    ts_findings = detect_typosquat(package_name, known_packages)
    findings.extend(ts_findings)

    # Dependency confusion
    dc = detect_dependency_confusion(
        package_name,
        private_registries=[expected_registry],
        public_registry="npm",
        current_registry=current_registry,
    )
    if dc:
        findings.append(dc)

    # Account takeover
    if current_publisher:
        at = detect_account_takeover(
            package_name,
            current_publisher,
            previous_publishers,
            package_age_days,
        )
        if at:
            findings.append(at)

    # Build injection
    if declared_hash and actual_hash:
        bi = detect_build_injection(package_name, declared_hash, actual_hash)
        if bi:
            findings.append(bi)

    # Die clash
    dc2 = detect_die_clash(package_name, foreign_files)
    if dc2:
        findings.append(dc2)

    # Provenance gap
    pg = detect_provenance_gap(package_name, provenance_level)
    if pg:
        findings.append(pg)

    return findings
