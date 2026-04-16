"""Tests for mint.provenance — Provenance chain verification."""

import pytest
from datetime import datetime, timezone

from mint.provenance import (
    create_provenance_chain,
    determine_provenance_level,
    find_provenance_gaps,
    format_provenance_report,
    verify_mint_mark_consistency,
)
from mint.models import MintMark, ProvenanceLevel


class TestCreateProvenanceChain:
    """Test provenance chain creation."""

    def test_full_chain(self):
        """Full chain with all three steps."""
        chain = create_provenance_chain(
            "test-pkg",
            source_commit="abc123",
            build_system="github-actions",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            publish_signature="sig3",
            source_verified=True,
            build_verified=True,
            publish_verified=True,
        )
        assert chain.package == "test-pkg"
        assert len(chain.chain) == 3

    def test_partial_chain(self):
        """Chain with only publish step."""
        chain = create_provenance_chain(
            "test-pkg",
            publish_registry="npm",
            publish_actor="bot",
        )
        assert len(chain.chain) == 1

    def test_empty_chain(self):
        """Chain with no steps."""
        chain = create_provenance_chain("test-pkg")
        assert len(chain.chain) == 0


class TestDetermineProvenanceLevel:
    """Test provenance level determination."""

    def test_level_0_no_chain(self):
        """Empty chain = Level 0."""
        chain = create_provenance_chain("pkg")
        assert determine_provenance_level(chain) == ProvenanceLevel.UNVERIFIED

    def test_level_0_unsigned(self):
        """Chain with no signatures = Level 0."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc123",
            build_system="github-actions",
            publish_registry="npm",
        )
        assert determine_provenance_level(chain) == ProvenanceLevel.UNVERIFIED

    def test_level_1_build_signed(self):
        """Build signed but no source link = Level 1."""
        chain = create_provenance_chain(
            "pkg",
            build_system="github-actions",
            build_signature="sig1",
            publish_registry="npm",
        )
        assert determine_provenance_level(chain) == ProvenanceLevel.BUILD_SIGNED

    def test_level_2_source_linked(self):
        """Source linked + build signed = Level 2."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc123",
            build_system="github-actions",
            build_signature="sig1",
            publish_registry="npm",
        )
        assert determine_provenance_level(chain) == ProvenanceLevel.SOURCE_LINKED

    def test_level_3_end_to_end(self):
        """All steps signed and verified = Level 3."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc123",
            build_system="github-actions",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            publish_signature="sig3",
            source_verified=True,
            build_verified=True,
            publish_verified=True,
        )
        assert determine_provenance_level(chain) == ProvenanceLevel.END_TO_END


class TestFindProvenanceGaps:
    """Test provenance gap detection."""

    def test_no_gaps(self):
        """Fully signed chain should have no gaps."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc",
            build_system="gha",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            publish_signature="sig3",
            source_verified=True,
            build_verified=True,
            publish_verified=True,
        )
        gaps = find_provenance_gaps(chain)
        assert len(gaps) == 0

    def test_unsigned_gap(self):
        """Unsigned step should be a gap."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc",
            build_system="gha",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            # publish_signature missing
            publish_actor="bot",
        )
        gaps = find_provenance_gaps(chain)
        assert len(gaps) >= 1
        assert any(g["gap_type"] == "unsigned" for g in gaps)

    def test_unverified_gap(self):
        """Signed but unverified step should be a gap."""
        chain = create_provenance_chain(
            "pkg",
            source_commit="abc",
            build_system="gha",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            publish_signature="sig3",
            source_verified=True,
            build_verified=True,
            publish_verified=False,  # Not verified
        )
        gaps = find_provenance_gaps(chain)
        assert len(gaps) >= 1
        assert any(g["gap_type"] == "unverified" for g in gaps)


class TestFormatProvenanceReport:
    """Test provenance report formatting."""

    def test_report_output(self):
        chain = create_provenance_chain(
            "express",
            source_commit="abc1234",
            build_system="github-actions",
            publish_registry="npm",
            source_signature="sig1",
            build_signature="sig2",
            publish_actor="express-bot",
            source_verified=True,
            build_verified=True,
        )
        report = format_provenance_report(chain)
        assert "Level" in report
        assert "VERIFIED" in report or "SIGNED" in report or "GAP" in report


class TestVerifyMintMarkConsistency:
    """Test mint mark verification."""

    def test_consistent_mint_mark(self):
        """Same publisher and registry should have no warnings."""
        current = MintMark(registry="npm", publisher="team-a", publisher_key="key123")
        previous = MintMark(registry="npm", publisher="team-a", publisher_key="key123")
        warnings = verify_mint_mark_consistency(current, previous, expected_registry="npm")
        assert len(warnings) == 0

    def test_registry_mismatch(self):
        """Different registry should warn."""
        current = MintMark(registry="evil-registry", publisher="team-a")
        warnings = verify_mint_mark_consistency(current, expected_registry="npm")
        assert any("Registry mismatch" in w for w in warnings)

    def test_publisher_key_change(self):
        """Changed publisher key should warn."""
        current = MintMark(registry="npm", publisher="team-a", publisher_key="new-key")
        previous = MintMark(registry="npm", publisher="team-a", publisher_key="old-key")
        warnings = verify_mint_mark_consistency(current, previous)
        assert any("Publisher key changed" in w for w in warnings)

    def test_no_build_signature(self):
        """Missing build signature should warn."""
        current = MintMark(registry="npm", publisher="team-a", build_signature="")
        warnings = verify_mint_mark_consistency(current, expected_registry="npm")
        assert any("No build signature" in w for w in warnings)

    def test_no_previous_version(self):
        """First version should not warn about publisher change."""
        current = MintMark(registry="npm", publisher="anyone", publisher_key="key1")
        warnings = verify_mint_mark_consistency(current, previous=None, expected_registry="npm")
        # No publisher change warnings for first version
        assert not any("Publisher key changed" in w for w in warnings)
