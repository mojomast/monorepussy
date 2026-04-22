"""Tests for operon.storage module."""

import pytest

from operon.models import (
    Codebase,
    Enhancer,
    EpigeneticMark,
    FactorType,
    Gene,
    MarkType,
    Operon,
    Promoter,
    Repressor,
    RepressorType,
    TranscriptionFactor,
)
from operon.storage import StorageManager


@pytest.fixture
def storage():
    return StorageManager(":memory:")


class TestOperonStorage:
    def test_save_and_load_operon(self, storage):
        gene = Gene(name="auth", path="auth.py", exports=["login"])
        operon = Operon(operon_id="op_0", genes=[gene], coupling_score=0.85)
        storage.save_operon(operon)

        loaded = storage.load_operons()
        assert len(loaded) == 1
        assert loaded[0].operon_id == "op_0"
        assert loaded[0].coupling_score == 0.85
        assert len(loaded[0].genes) == 1

    def test_delete_operon(self, storage):
        operon = Operon(operon_id="op_0", genes=[])
        storage.save_operon(operon)
        storage.delete_operon("op_0")
        assert len(storage.load_operons()) == 0


class TestPromoterStorage:
    def test_save_and_load_promoter(self, storage):
        p = Promoter(promoter_id="p1", trigger_type="api", strength=1.0, transcription_rate=0.8)
        storage.save_promoter(p)

        loaded = storage.load_promoters()
        assert len(loaded) == 1
        assert loaded[0].promoter_id == "p1"
        assert loaded[0].strength == 1.0

    def test_delete_promoter(self, storage):
        p = Promoter(promoter_id="p1", trigger_type="api", strength=0.5)
        storage.save_promoter(p)
        storage.delete_promoter("p1")
        assert len(storage.load_promoters()) == 0


class TestRepressorStorage:
    def test_save_and_load_repressor(self, storage):
        r = Repressor(
            repressor_id="r1",
            repressor_type=RepressorType.INDUCIBLE,
            operator_site="old.py",
        )
        storage.save_repressor(r)

        loaded = storage.load_repressors()
        assert len(loaded) == 1
        assert loaded[0].repressor_type == RepressorType.INDUCIBLE

    def test_delete_repressor(self, storage):
        r = Repressor(repressor_id="r1", repressor_type=RepressorType.CONSTITUTIVE)
        storage.save_repressor(r)
        storage.delete_repressor("r1")
        assert len(storage.load_repressors()) == 0


class TestEnhancerStorage:
    def test_save_and_load_enhancer(self, storage):
        e = Enhancer(
            enhancer_id="e1",
            source_gene="a.py",
            target_gene="b.py",
            enhancer_strength=0.9,
        )
        storage.save_enhancer(e)

        loaded = storage.load_enhancers()
        assert len(loaded) == 1
        assert loaded[0].enhancer_strength == 0.9

    def test_delete_enhancer(self, storage):
        e = Enhancer(enhancer_id="e1", source_gene="a.py", target_gene="b.py")
        storage.save_enhancer(e)
        storage.delete_enhancer("e1")
        assert len(storage.load_enhancers()) == 0


class TestTranscriptionFactorStorage:
    def test_save_and_load_factor(self, storage):
        tf = TranscriptionFactor(
            factor_id="tf1",
            name="expert",
            factor_type=FactorType.ACTIVATOR,
        )
        storage.save_transcription_factor(tf)

        loaded = storage.load_transcription_factors()
        assert len(loaded) == 1
        assert loaded[0].factor_type == FactorType.ACTIVATOR

    def test_delete_factor(self, storage):
        tf = TranscriptionFactor(factor_id="tf1", name="expert", factor_type=FactorType.REPRESSOR)
        storage.save_transcription_factor(tf)
        storage.delete_transcription_factor("tf1")
        assert len(storage.load_transcription_factors()) == 0


class TestEpigeneticMarkStorage:
    def test_save_and_load_mark(self, storage):
        m = EpigeneticMark(
            mark_id="m1",
            operon_id="op_0",
            mark_type=MarkType.ACETYLATION,
            level=0.8,
        )
        storage.save_epigenetic_mark(m)

        loaded = storage.load_epigenetic_marks()
        assert len(loaded) == 1
        assert loaded[0].mark_type == MarkType.ACETYLATION
        assert loaded[0].level == 0.8

    def test_delete_mark(self, storage):
        m = EpigeneticMark(mark_id="m1", operon_id="op_0", mark_type=MarkType.METHYLATION)
        storage.save_epigenetic_mark(m)
        storage.delete_epigenetic_mark("m1")
        assert len(storage.load_epigenetic_marks()) == 0


class TestCodebaseStorage:
    def test_save_and_load_codebase(self, storage):
        cb = Codebase(root_path="/src", genes=[Gene(name="a", path="a.py")])
        storage.save_codebase(cb)

        loaded = storage.load_codebases()
        assert len(loaded) == 1
        assert loaded[0].root_path == "/src"
        assert len(loaded[0].genes) == 1


class TestStorageClear:
    def test_clear_all(self, storage):
        storage.save_operon(Operon(operon_id="op_0", genes=[]))
        storage.save_promoter(Promoter(promoter_id="p1", trigger_type="api"))
        storage.clear_all()
        assert len(storage.load_operons()) == 0
        assert len(storage.load_promoters()) == 0


class TestStorageClose:
    def test_close_and_reopen(self, storage):
        storage.save_operon(Operon(operon_id="op_0", genes=[]))
        # Before close, data exists
        loaded = storage.load_operons()
        assert len(loaded) == 1
        storage.close()
        # After close, the connection is reset but in-memory DB is gone
        # This test just verifies close doesn't crash
        assert storage._connection is None
