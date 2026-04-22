"""Tests for crystallo.classify — space group assignment and unit cell detection."""

import pytest
from pathlib import Path

from ussy_crystallo.models import (
    ModuleClassification,
    SpaceGroup,
    StructuralFingerprint,
    SymmetryType,
    UnitCell,
)
from ussy_crystallo.classify import (
    classify_module,
    detect_unit_cells,
    _assign_space_group,
    _crystal_system_name,
)
from ussy_crystallo.parser import parse_directory
from ussy_crystallo.similarity import compute_pairwise_similarities


FIXTURES = Path(__file__).parent / "fixtures"


class TestAssignSpaceGroup:
    def test_no_units_p1(self):
        assert _assign_space_group(0, 0, 0, 0, 0, 0) == SpaceGroup.P1

    def test_low_symmetry_p1(self):
        assert _assign_space_group(5, 0, 0, 0, 0, 0) == SpaceGroup.P1

    def test_single_reflection_pm(self):
        assert _assign_space_group(5, 0, 1, 0, 0, 0) == SpaceGroup.Pm

    def test_single_rotation_p2(self):
        assert _assign_space_group(5, 1, 0, 0, 0, 0) == SpaceGroup.P2

    def test_rotation_and_reflection_p2m(self):
        assert _assign_space_group(5, 1, 1, 0, 0, 0) == SpaceGroup.P2m

    def test_high_translational_p6(self):
        assert _assign_space_group(10, 0, 0, 3, 0, 0) == SpaceGroup.P6

    def test_four_fold_rotational_p4(self):
        assert _assign_space_group(10, 4, 0, 0, 0, 0) == SpaceGroup.P4

    def test_multi_axis_cubic(self):
        assert _assign_space_group(15, 3, 2, 2, 0, 0) == SpaceGroup.Pa3

    def test_broken_dominates_p1(self):
        # Broken (3) > total_sym (1), so P1
        assert _assign_space_group(5, 0, 0, 0, 0, 3) == SpaceGroup.P1

    def test_glide_symmetry_pm(self):
        assert _assign_space_group(5, 0, 0, 0, 1, 0) == SpaceGroup.Pm


class TestCrystalSystemName:
    def test_p1_triclinic(self):
        assert _crystal_system_name(SpaceGroup.P1) == "Triclinic"

    def test_pm_monoclinic(self):
        assert _crystal_system_name(SpaceGroup.Pm) == "Monoclinic"

    def test_p4_tetragonal(self):
        assert _crystal_system_name(SpaceGroup.P4) == "Tetragonal"

    def test_p6_hexagonal(self):
        assert _crystal_system_name(SpaceGroup.P6) == "Hexagonal"

    def test_pa3_cubic(self):
        assert _crystal_system_name(SpaceGroup.Pa3) == "Cubic"


class TestClassifyModule:
    def test_classify_models_dir(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        cls = classify_module(str(FIXTURES), fps, rels)
        assert isinstance(cls, ModuleClassification)
        assert cls.space_group in SpaceGroup
        assert cls.fingerprint_count > 0

    def test_classify_empty(self):
        cls = classify_module("/tmp/nonexistent", [], [])
        assert cls.space_group == SpaceGroup.P1
        assert cls.fingerprint_count == 0


class TestDetectUnitCells:
    def test_detect_clusters(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        cells = detect_unit_cells(fps, rels)
        # Models with shared base should cluster
        assert len(cells) >= 1

    def test_no_fingerprints(self):
        cells = detect_unit_cells([], [])
        assert cells == []

    def test_unit_cell_has_members(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        cells = detect_unit_cells(fps, rels)
        for cell in cells:
            assert cell.member_count >= 2
            assert cell.representative_name

    def test_unit_cell_space_group(self):
        fps = parse_directory(FIXTURES / "models.py")
        rels = compute_pairwise_similarities(fps)
        cells = detect_unit_cells(fps, rels)
        for cell in cells:
            assert isinstance(cell.space_group, SpaceGroup)
