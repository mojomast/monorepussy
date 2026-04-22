"""Tests for crystallo.defects — broken symmetry and accidental detection."""

import pytest
from pathlib import Path

from crystallo.models import (
    DefectReport,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryType,
)
from crystallo.defects import detect_defects, detect_translational_groups
from crystallo.parser import parse_directory
from crystallo.similarity import compute_pairwise_similarities


FIXTURES = Path(__file__).parent / "fixtures"


class TestDetectDefects:
    def test_detects_broken_symmetry(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        defects = detect_defects(fps, rels)
        broken = [d for d in defects if d.defect_type == "broken"]
        # UserModel vs OrderModel should show broken symmetry
        assert len(broken) >= 1

    def test_defect_has_confidence(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        defects = detect_defects(fps, rels)
        for d in defects:
            assert 0.0 <= d.confidence <= 1.0

    def test_empty_fingerprints(self):
        defects = detect_defects([], [])
        assert defects == []

    def test_defect_report_fields(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        defects = detect_defects(fps, rels)
        for d in defects:
            assert d.file_path
            assert d.unit_name
            assert d.defect_type in ("broken", "accidental", "intentional")

    def test_no_self_defects(self):
        """A fingerprint shouldn't create a defect with itself."""
        fp = StructuralFingerprint(name="Solo", method_names=["a", "b"])
        rels = compute_pairwise_similarities([fp])
        defects = detect_defects([fp], rels)
        assert len(defects) == 0


class TestDetectTranslationalGroups:
    def test_no_translational_with_few_units(self):
        fp = StructuralFingerprint(name="A", method_names=["save"])
        defects = detect_translational_groups([fp], [])
        assert defects == []

    def test_returns_defect_reports(self):
        fps = parse_directory(FIXTURES)
        rels = compute_pairwise_similarities(fps)
        groups = detect_translational_groups(fps, rels)
        for g in groups:
            assert isinstance(g, DefectReport)

    def test_empty_input(self):
        assert detect_translational_groups([], []) == []


class TestDefectWithAPI:
    def test_api_module_defects(self):
        fps = parse_directory(FIXTURES / "api.py")
        rels = compute_pairwise_similarities(fps)
        defects = detect_defects(fps, rels)
        # APIClient and APIServer should have reflection, not broken
        # but create_* functions may show translational
        assert isinstance(defects, list)
