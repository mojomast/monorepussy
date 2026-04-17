"""Tests for the traceability auditor module."""

import math
from datetime import datetime, timezone, timedelta

import pytest

from calibre.models import TraceabilityLink
from calibre.traceability import (
    audit_traceability,
    check_chain_completeness,
    compute_chain_uncertainty,
    compute_integrity_score,
    detect_orphan,
    detect_stale_links,
    format_traceability,
)


class TestComputeChainUncertainty:
    def test_empty_chain(self):
        assert compute_chain_uncertainty([]) == float("inf")

    def test_single_link(self):
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
            )
        ]
        result = compute_chain_uncertainty(links)
        assert abs(result - 0.05) < 1e-10

    def test_multiple_links(self):
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.03,
            ),
            TraceabilityLink(
                test_name="t1", level="assertion",
                reference="assert x", uncertainty=0.04,
            ),
        ]
        result = compute_chain_uncertainty(links)
        expected = math.sqrt(0.03**2 + 0.04**2)
        assert abs(result - expected) < 1e-10


class TestDetectOrphan:
    def test_orphan(self):
        assert detect_orphan([]) is True

    def test_not_orphan(self):
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
            )
        ]
        assert detect_orphan(links) is False


class TestDetectStaleLinks:
    def test_no_stale(self):
        now = datetime.now(timezone.utc)
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
                last_verified=now - timedelta(days=10),
                review_interval_days=90,
            )
        ]
        stale = detect_stale_links(links, now=now)
        assert len(stale) == 0

    def test_stale(self):
        now = datetime.now(timezone.utc)
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
                last_verified=now - timedelta(days=200),
                review_interval_days=90,
            )
        ]
        stale = detect_stale_links(links, now=now)
        assert len(stale) == 1
        assert "REQ-1" in stale

    def test_never_verified(self):
        now = datetime.now(timezone.utc)
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
                last_verified=None,
            )
        ]
        stale = detect_stale_links(links, now=now)
        assert len(stale) == 1


class TestCheckChainCompleteness:
    def test_empty_chain(self):
        assert check_chain_completeness([]) == 0.0

    def test_full_chain(self, sample_traceability_links):
        completeness = check_chain_completeness(sample_traceability_links)
        assert completeness == 1.0

    def test_partial_chain(self):
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
            ),
            TraceabilityLink(
                test_name="t1", level="assertion",
                reference="assert x", uncertainty=0.01,
            ),
        ]
        completeness = check_chain_completeness(links)
        assert 0.0 < completeness < 1.0


class TestComputeIntegrityScore:
    def test_perfect_score(self):
        score = compute_integrity_score(
            completeness=1.0, chain_uncertainty=0.0, has_stale=False,
        )
        assert score == 1.0

    def test_incomplete_penalty(self):
        score = compute_integrity_score(
            completeness=0.5, chain_uncertainty=0.0, has_stale=False,
        )
        assert score == 0.5

    def test_stale_penalty(self):
        score_no_stale = compute_integrity_score(
            completeness=1.0, chain_uncertainty=0.0, has_stale=False,
        )
        score_stale = compute_integrity_score(
            completeness=1.0, chain_uncertainty=0.0, has_stale=True,
        )
        assert score_stale < score_no_stale

    def test_uncertainty_penalty(self):
        score_low_u = compute_integrity_score(
            completeness=1.0, chain_uncertainty=0.1, has_stale=False,
        )
        score_high_u = compute_integrity_score(
            completeness=1.0, chain_uncertainty=0.5, has_stale=False,
        )
        assert score_high_u < score_low_u


class TestAuditTraceability:
    def test_orphan(self):
        result = audit_traceability("orphan_test", [])
        assert result.is_orphan is True
        assert "ORPHAN" in result.diagnosis

    def test_complete_chain(self, sample_traceability_links):
        result = audit_traceability("test_login", sample_traceability_links)
        assert result.is_orphan is False
        assert result.chain_uncertainty > 0.0
        assert result.integrity_score > 0.0

    def test_stale_chain(self):
        now = datetime.now(timezone.utc)
        links = [
            TraceabilityLink(
                test_name="t1", level="specification",
                reference="REQ-1", uncertainty=0.05,
                last_verified=now - timedelta(days=400),
                review_interval_days=90,
            ),
        ]
        result = audit_traceability("t1", links, now=now)
        assert result.has_stale_links is True
        assert "STALE" in result.diagnosis


class TestFormatTraceability:
    def test_format_orphan(self):
        result = audit_traceability("orphan_test", [])
        output = format_traceability(result)
        assert "ORPHAN" in output

    def test_format_complete(self, sample_traceability_links):
        result = audit_traceability("test_login", sample_traceability_links)
        output = format_traceability(result)
        assert "Traceability Audit" in output
        assert "Chain uncertainty" in output
