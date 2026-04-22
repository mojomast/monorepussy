"""Provenance chain verification — chain of custody for packages.

Verifies the complete chain from source commit through build to publish,
assigning a provenance level based on how many links are verified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from mint.models import (
    MintMark,
    ProvenanceChain,
    ProvenanceLink,
    ProvenanceLevel,
    PackageInfo,
)


def create_provenance_chain(
    package_name: str,
    source_commit: str = "",
    build_system: str = "",
    publish_registry: str = "",
    source_signature: str = "",
    build_signature: str = "",
    publish_signature: str = "",
    source_actor: str = "",
    build_actor: str = "",
    publish_actor: str = "",
    source_verified: bool = False,
    build_verified: bool = False,
    publish_verified: bool = False,
) -> ProvenanceChain:
    """Create a provenance chain for a package version.

    Builds the chain of custody from source → build → publish.

    Args:
        package_name: Package name
        source_commit: Source commit hash
        build_system: Build system identifier (e.g., "github-actions")
        publish_registry: Registry where published (e.g., "npm")
        source_signature: Cryptographic signature at source
        build_signature: Cryptographic signature at build
        publish_signature: Cryptographic signature at publish
        source_actor: Who/what created the source commit
        build_actor: Who/what ran the build
        publish_actor: Who/what published the package
        source_verified: Whether source step was independently verified
        build_verified: Whether build step was independently verified
        publish_verified: Whether publish step was independently verified

    Returns:
        ProvenanceChain with links populated
    """
    chain: list[ProvenanceLink] = []

    if source_commit:
        chain.append(ProvenanceLink(
            source=f"source-commit:{source_commit}",
            actor=source_actor or "unknown",
            signature=source_signature,
            verified=source_verified,
        ))

    if build_system:
        chain.append(ProvenanceLink(
            source=f"build:{build_system}",
            actor=build_actor or "unknown",
            signature=build_signature,
            verified=build_verified,
        ))

    if publish_registry:
        chain.append(ProvenanceLink(
            source=f"publish:{publish_registry}",
            actor=publish_actor or "unknown",
            signature=publish_signature,
            verified=publish_verified,
        ))

    return ProvenanceChain(package=package_name, chain=chain)


def determine_provenance_level(chain: ProvenanceChain) -> ProvenanceLevel:
    """Determine the provenance verification level of a chain.

    Levels:
    - Level 0: No verified links, no signatures
    - Level 1: Build artifact is signed (mint is identified)
    - Level 2: Build links to a specific source commit (die is identified)
    - Level 3: Full end-to-end verified chain

    Args:
        chain: ProvenanceChain to evaluate

    Returns:
        ProvenanceLevel enum value
    """
    if not chain.chain:
        return ProvenanceLevel.UNVERIFIED

    has_source = False
    has_build = False
    has_publish = False
    source_signed = False
    build_signed = False
    publish_signed = False
    all_verified = True

    for link in chain.chain:
        if link.source.startswith("source-commit:"):
            has_source = True
            source_signed = bool(link.signature)
            if not link.verified:
                all_verified = False
        elif link.source.startswith("build:"):
            has_build = True
            build_signed = bool(link.signature)
            if not link.verified:
                all_verified = False
        elif link.source.startswith("publish:"):
            has_publish = True
            publish_signed = bool(link.signature)
            if not link.verified:
                all_verified = False

    # Level 3: End-to-end verified
    if has_source and has_build and has_publish and all_verified and source_signed and build_signed and publish_signed:
        return ProvenanceLevel.END_TO_END

    # Level 2: Source-linked (build links to source)
    if has_source and has_build and build_signed:
        return ProvenanceLevel.SOURCE_LINKED

    # Level 1: Build-signed
    if has_build and build_signed:
        return ProvenanceLevel.BUILD_SIGNED

    # Level 0: Unverified
    return ProvenanceLevel.UNVERIFIED


def find_provenance_gaps(chain: ProvenanceChain) -> list[dict]:
    """Identify gaps in the provenance chain.

    A gap is a link that is unsigned or unverified.

    Args:
        chain: ProvenanceChain to check

    Returns:
        List of dicts describing each gap
    """
    gaps = []
    for link in chain.chain:
        if not link.signature:
            gaps.append({
                "source": link.source,
                "actor": link.actor,
                "gap_type": "unsigned",
                "description": f"Step '{link.source}' by '{link.actor}' is unsigned",
            })
        elif not link.verified:
            gaps.append({
                "source": link.source,
                "actor": link.actor,
                "gap_type": "unverified",
                "description": f"Step '{link.source}' by '{link.actor}' is signed but not independently verified",
            })
    return gaps


def format_provenance_report(chain: ProvenanceChain) -> str:
    """Format a provenance chain as a human-readable report.

    Args:
        chain: ProvenanceChain to format

    Returns:
        Formatted report string
    """
    level = determine_provenance_level(chain)
    lines = [f"Provenance chain: Level {int(level)} ({level.name})"]

    for link in chain.chain:
        if link.verified and link.signature:
            status = "[VERIFIED]"
        elif link.signature:
            status = "[SIGNED]"
        else:
            status = "[GAP]"

        sig_info = " (signed)" if link.signature else " (unsigned)"
        repro_info = " (reproducible)" if link.verified else ""
        lines.append(f"  {status} {link.source} by {link.actor}{sig_info}{repro_info}")

    gaps = find_provenance_gaps(chain)
    if gaps:
        lines.append(f"\n  ⚠️ {len(gaps)} provenance gap(s) detected")

    return "\n".join(lines)


def verify_mint_mark_consistency(
    current: MintMark,
    previous: MintMark | None = None,
    expected_registry: str = "npm",
) -> list[str]:
    """Verify mint mark consistency between versions.

    Checks for:
    - Registry consistency (dependency confusion)
    - Publisher continuity (account takeover)
    - Build signature presence

    Args:
        current: Current version's mint mark
        previous: Previous version's mint mark (None for first version)
        expected_registry: Expected registry for this package

    Returns:
        List of warning strings for any inconsistencies
    """
    warnings = []

    # Registry check
    if current.registry != expected_registry:
        warnings.append(
            f"Registry mismatch: package from '{current.registry}', expected '{expected_registry}'"
        )

    # Publisher continuity check
    if previous:
        if current.publisher != previous.publisher:
            warnings.append(
                f"Publisher changed: '{previous.publisher}' → '{current.publisher}'"
            )
        if current.publisher_key and previous.publisher_key:
            if current.publisher_key != previous.publisher_key:
                warnings.append(
                    f"Publisher key changed: '{previous.publisher_key[:16]}...' → '{current.publisher_key[:16]}...'"
                )

    # Build signature check
    if not current.build_signature:
        if previous is None:
            warnings.append("No build signature present")
        elif previous.build_signature:
            warnings.append("Build signature lost")

    return warnings
