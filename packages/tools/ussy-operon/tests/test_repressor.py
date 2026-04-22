"""Tests for operon.repressor module."""

import pytest

from operon.models import Codebase, Gene, RepressorType
from operon.repressor import RepressorManager


class TestRepressorManager:
    def test_manager_creation(self):
        manager = RepressorManager()
        assert manager.repressors == []

    def test_create_laci_repressor_deprecated(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        rep = manager._create_laci_repressor(gene)
        assert rep.repressor_type == RepressorType.INDUCIBLE
        assert rep.allosteric_state == "active"
        assert rep.repression_level == 1.0

    def test_create_laci_repressor_not_deprecated(self):
        manager = RepressorManager()
        gene = Gene(name="new", path="new.py", is_deprecated=False)
        rep = manager._create_laci_repressor(gene)
        assert rep.allosteric_state == "inactive"
        assert rep.repression_level == 0.0

    def test_create_trpr_repressor(self):
        manager = RepressorManager()
        gene = Gene(name="internal", path="internal.py")
        rep = manager._create_trpr_repressor(gene)
        assert rep.repressor_type == RepressorType.COREPRESSOR_DEPENDENT
        assert rep.corepressor == "@internal_tag"
        assert rep.repression_level == 1.0

    def test_create_constitutive_repressor(self):
        manager = RepressorManager()
        gene = Gene(name="_private", path="_private.py")
        rep = manager._create_constitutive_repressor(gene)
        assert rep.repressor_type == RepressorType.CONSTITUTIVE
        assert rep.repression_level == 1.0

    def test_manage_repressors_empty(self):
        manager = RepressorManager()
        codebase = Codebase(root_path=".")
        reps = manager.manage_repressors(codebase)
        assert reps == []

    def test_manage_repressors_deprecated(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        codebase = Codebase(root_path=".", deprecated_features=[gene])
        reps = manager.manage_repressors(codebase)
        assert len(reps) == 1
        assert reps[0].repressor_type == RepressorType.INDUCIBLE

    def test_manage_repressors_internal(self):
        manager = RepressorManager()
        gene = Gene(name="internal", path="internal.py", is_internal=True)
        codebase = Codebase(root_path=".", internal_apis=[gene])
        reps = manager.manage_repressors(codebase)
        assert len(reps) == 1
        assert reps[0].repressor_type == RepressorType.COREPRESSOR_DEPENDENT

    def test_manage_repressors_private(self):
        manager = RepressorManager()
        gene = Gene(name="_util", path="_util.py")
        codebase = Codebase(root_path=".", genes=[gene])
        reps = manager.manage_repressors(codebase)
        assert len(reps) == 1
        assert reps[0].repressor_type == RepressorType.CONSTITUTIVE

    def test_lift_repression_inducible(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[gene]))
        success = manager.lift_repression(manager.repressors[0].repressor_id)
        assert success is True
        assert manager.repressors[0].repression_level == 0.0

    def test_lift_repression_wrong_id(self):
        manager = RepressorManager()
        success = manager.lift_repression("nonexistent")
        assert success is False

    def test_apply_repression(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[gene]))
        manager.lift_repression(manager.repressors[0].repressor_id)
        manager.apply_repression(manager.repressors[0].repressor_id)
        assert manager.repressors[0].repression_level == 1.0

    def test_is_repressed_true(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[gene]))
        assert manager.is_repressed("old.py") is True

    def test_is_repressed_false(self):
        manager = RepressorManager()
        gene = Gene(name="new", path="new.py", is_deprecated=False)
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[gene]))
        assert manager.is_repressed("new.py") is False

    def test_get_repression_level(self):
        manager = RepressorManager()
        gene = Gene(name="old", path="old.py", is_deprecated=True)
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[gene]))
        assert manager.get_repression_level("old.py") == 1.0

    def test_get_repression_level_no_repressor(self):
        manager = RepressorManager()
        assert manager.get_repression_level("unknown.py") == 0.0

    def test_filter_visible_genes(self):
        manager = RepressorManager()
        g1 = Gene(name="old", path="old.py", is_deprecated=True)
        g2 = Gene(name="new", path="new.py")
        manager.manage_repressors(Codebase(root_path=".", deprecated_features=[g1], genes=[g1, g2]))
        visible = manager.filter_visible_genes([g1, g2])
        assert len(visible) == 1
        assert visible[0].path == "new.py"

    def test_add_custom_repressor(self):
        manager = RepressorManager()
        rep = manager.add_custom_repressor(
            feature_path="custom.py",
            repressor_type=RepressorType.INDUCIBLE,
            repression_level=0.8,
        )
        assert rep.repressor_type == RepressorType.INDUCIBLE
        assert rep.repression_level == 0.8
        assert len(manager.repressors) == 1

    def test_add_custom_repressor_with_inducer(self):
        manager = RepressorManager()
        rep = manager.add_custom_repressor(
            feature_path="custom.py",
            repressor_type=RepressorType.COREPRESSOR_DEPENDENT,
            corepressor="@internal",
        )
        assert rep.corepressor == "@internal"
