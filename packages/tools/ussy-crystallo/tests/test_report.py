"""Tests for crystallo.report — output formatting."""

import pytest

from ussy_crystallo.models import (
    DefectReport,
    ModuleClassification,
    SpaceGroup,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
    UnitCell,
)
from ussy_crystallo.report import (
    format_classification,
    format_defects,
    format_fingerprint_summary,
    format_symmetry_relations,
    format_unit_cells,
)


class TestFormatSymmetryRelations:
    def test_empty(self):
        assert "No significant symmetry" in format_symmetry_relations([])

    def test_single_relation(self):
        rel = SymmetryRelation(
            source="A", target="B",
            symmetry_type=SymmetryType.ROTATIONAL,
            intent=SymmetryIntent.INTENTIONAL,
            similarity=0.85,
        )
        output = format_symmetry_relations([rel])
        assert "Cn" in output
        assert "A ↔ B" in output
        assert "INTENTIONAL" in output

    def test_with_missing_methods(self):
        rel = SymmetryRelation(
            source="A", target="B",
            symmetry_type=SymmetryType.BROKEN,
            missing_in_target=["validate"],
            similarity=0.7,
        )
        output = format_symmetry_relations([rel])
        assert "Missing in B" in output


class TestFormatUnitCells:
    def test_empty(self):
        assert "No repeating" in format_unit_cells([])

    def test_single_cell(self):
        uc = UnitCell(
            representative_name="BaseModel",
            member_names=["UserModel", "OrderModel"],
            symmetry_type=SymmetryType.ROTATIONAL,
            space_group=SpaceGroup.P2,
            member_count=2,
            avg_similarity=0.8,
        )
        output = format_unit_cells([uc])
        assert "BaseModel" in output
        assert "P2" in output
        assert "UserModel" in output


class TestFormatDefects:
    def test_empty(self):
        assert "No symmetry defects" in format_defects([])

    def test_broken_defect(self):
        d = DefectReport(
            file_path="models.py",
            unit_name="OrderModel",
            expected_symmetry_with="UserModel",
            defect_type="broken",
            missing_features=["validate_email", "soft_delete"],
            confidence=0.87,
        )
        output = format_defects([d])
        assert "BROKEN" in output
        assert "OrderModel" in output
        assert "validate_email" in output

    def test_accidental_defect(self):
        d = DefectReport(
            file_path="api.py",
            unit_name="create_user",
            expected_symmetry_with="create_order",
            defect_type="accidental",
            confidence=0.94,
            suggestion="Consider extracting shared abstraction",
        )
        output = format_defects([d])
        assert "ACCIDENTAL" in output


class TestFormatClassification:
    def test_basic(self):
        cls = ModuleClassification(
            path="/src/models",
            space_group=SpaceGroup.Pm,
            symmetry_description="Monoclinic system; 1 reflection pair(s)",
            fingerprint_count=5,
            rotational_pairs=0,
            reflection_pairs=1,
            translational_groups=0,
            broken_count=2,
        )
        output = format_classification(cls)
        assert "Pm" in output
        assert "/src/models" in output


class TestFormatFingerprintSummary:
    def test_empty(self):
        assert "No structural units" in format_fingerprint_summary([])

    def test_class_fingerprint(self):
        fp = StructuralFingerprint(
            name="UserModel",
            kind="class",
            method_names=["save", "delete"],
            base_classes=["Base"],
        )
        output = format_fingerprint_summary([fp])
        assert "UserModel" in output
        assert "save" in output

    def test_function_fingerprint(self):
        from ussy_crystallo.models import MethodSignature
        fp = StructuralFingerprint(
            name="create_user",
            kind="function",
            method_signatures=[
                MethodSignature(name="create_user", arg_count=2)
            ],
        )
        output = format_fingerprint_summary([fp])
        assert "create_user" in output
