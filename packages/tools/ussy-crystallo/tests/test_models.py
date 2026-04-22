"""Tests for crystallo.models — data model construction and validation."""

import pytest

from ussy_crystallo.models import (
    DefectReport,
    MethodSignature,
    ModuleClassification,
    SpaceGroup,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
    UnitCell,
)


# ---------------------------------------------------------------------------
# StructuralFingerprint
# ---------------------------------------------------------------------------

class TestStructuralFingerprint:
    def test_basic_creation(self):
        fp = StructuralFingerprint(name="Foo")
        assert fp.name == "Foo"
        assert fp.kind == "class"
        assert fp.feature_vector  # auto-computed

    def test_feature_vector_computed(self):
        fp = StructuralFingerprint(
            name="Bar",
            method_names=["a", "b", "c"],
            attribute_names=["x", "y"],
            base_classes=["Base"],
            decorator_names=["dataclass"],
            has_init=True,
        )
        assert len(fp.feature_vector) == 15  # fixed-length vector
        assert fp.feature_vector[0] == 3.0  # len(method_names)
        assert fp.feature_vector[1] == 2.0  # len(attribute_names)
        assert fp.feature_vector[2] == 1.0  # len(base_classes)
        assert fp.feature_vector[3] == 1.0  # len(decorator_names)
        assert fp.feature_vector[4] == 1.0  # has_init

    def test_method_set_computed(self):
        fp = StructuralFingerprint(name="X", method_names=["save", "delete", "save"])
        assert fp.method_set == {"save", "delete"}

    def test_attribute_set_computed(self):
        fp = StructuralFingerprint(name="X", attribute_names=["id", "name", "id"])
        assert fp.attribute_set == {"id", "name"}

    def test_empty_fingerprint(self):
        fp = StructuralFingerprint(name="Empty")
        assert fp.feature_vector
        assert all(v == 0.0 for v in fp.feature_vector)

    def test_function_kind(self):
        fp = StructuralFingerprint(name="my_func", kind="function")
        assert fp.kind == "function"
        assert fp.feature_vector  # still computed

    def test_with_method_signatures(self):
        sig = MethodSignature(name="save", arg_count=2, has_return_annotation=True)
        fp = StructuralFingerprint(name="C", method_signatures=[sig])
        assert fp.feature_vector[7] == 1.0  # has_return_annotation count


# ---------------------------------------------------------------------------
# MethodSignature
# ---------------------------------------------------------------------------

class TestMethodSignature:
    def test_defaults(self):
        sig = MethodSignature(name="foo")
        assert sig.arg_count == 0
        assert not sig.is_async
        assert not sig.is_classmethod
        assert not sig.is_staticmethod

    def test_async_method(self):
        sig = MethodSignature(name="fetch", is_async=True)
        assert sig.is_async


# ---------------------------------------------------------------------------
# SymmetryRelation
# ---------------------------------------------------------------------------

class TestSymmetryRelation:
    def test_creation(self):
        rel = SymmetryRelation(
            source="A", target="B",
            symmetry_type=SymmetryType.ROTATIONAL,
            intent=SymmetryIntent.INTENTIONAL,
            similarity=0.85,
        )
        assert rel.source == "A"
        assert rel.target == "B"
        assert rel.symmetry_type == SymmetryType.ROTATIONAL

    def test_default_lists(self):
        rel = SymmetryRelation(source="A", target="B")
        assert rel.missing_in_source == []
        assert rel.missing_in_target == []


# ---------------------------------------------------------------------------
# UnitCell
# ---------------------------------------------------------------------------

class TestUnitCell:
    def test_member_count_auto(self):
        uc = UnitCell(
            representative_name="Base",
            member_names=["A", "B", "C"],
        )
        assert uc.member_count == 3

    def test_empty_member_count(self):
        uc = UnitCell(representative_name="Solo")
        assert uc.member_count == 0


# ---------------------------------------------------------------------------
# SpaceGroup
# ---------------------------------------------------------------------------

class TestSpaceGroup:
    def test_all_values(self):
        expected = {"P1", "Pm", "P2", "P2/m", "P4", "P6", "Pa3"}
        actual = {g.value for g in SpaceGroup}
        assert actual == expected

    def test_p1_is_lowest(self):
        assert SpaceGroup.P1.value == "P1"


# ---------------------------------------------------------------------------
# DefectReport
# ---------------------------------------------------------------------------

class TestDefectReport:
    def test_creation(self):
        dr = DefectReport(
            file_path="a.py",
            unit_name="A",
            expected_symmetry_with="B",
            defect_type="broken",
            confidence=0.9,
        )
        assert dr.defect_type == "broken"

    def test_defaults(self):
        dr = DefectReport(file_path="a.py", unit_name="A")
        assert dr.defect_type == "broken"
        assert dr.missing_features == []
        assert dr.confidence == 0.0


# ---------------------------------------------------------------------------
# ModuleClassification
# ---------------------------------------------------------------------------

class TestModuleClassification:
    def test_defaults(self):
        mc = ModuleClassification(path="/tmp/test")
        assert mc.space_group == SpaceGroup.P1
        assert mc.fingerprint_count == 0
