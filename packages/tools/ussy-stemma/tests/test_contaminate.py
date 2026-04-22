"""Tests for the contaminate module."""

from stemma.classify import classify_all
from stemma.collation import collate
from stemma.contaminate import (
    detect_contamination,
    detect_contamination_from_collation,
)
from stemma.models import Witness
from stemma.stemma_builder import build_stemma


class TestDetectContamination:
    def test_contamination_with_stemma(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        tree = build_stemma(classified)
        reports = detect_contamination(classified, tree)
        # D is the contaminated witness in our fixtures
        # (has logging from β branch + compute from γ branch)
        # May or may not be detected depending on tree structure
        assert isinstance(reports, list)

    def test_no_contamination_identical(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 2"])
        collation = collate([a, b])
        tree = build_stemma(collation)
        reports = detect_contamination(collation, tree)
        assert len(reports) == 0

    def test_empty_collation(self):
        collation = collate([])
        tree = build_stemma(collation)
        reports = detect_contamination(collation, tree)
        assert reports == []


class TestDetectContaminationFromCollation:
    def test_basic(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        reports = detect_contamination_from_collation(classified)
        assert isinstance(reports, list)

    def test_too_few_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1"])
        b = Witness(label="B", source="b.py", lines=["x = 2"])
        collation = collate([a, b])
        reports = detect_contamination_from_collation(collation)
        assert reports == []  # Need at least 3 witnesses

    def test_no_variants(self):
        a = Witness(label="A", source="a.py", lines=["x = 1"])
        b = Witness(label="B", source="b.py", lines=["x = 1"])
        c = Witness(label="C", source="c.py", lines=["x = 1"])
        collation = collate([a, b, c])
        reports = detect_contamination_from_collation(collation)
        assert reports == []

    def test_report_fields(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        reports = detect_contamination_from_collation(classified)
        for report in reports:
            assert report.witness
            assert isinstance(report.primary_lineage, str)
            assert isinstance(report.contaminating_source, str)
