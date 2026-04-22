"""Tests for operon.models module."""

import json
from datetime import datetime, timezone

import pytest

from ussy_operon.models import (
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
    serialize_to_json,
)


class TestGene:
    def test_gene_creation(self):
        gene = Gene(name="auth", path="src/auth.py", exports=["login", "logout"])
        assert gene.name == "auth"
        assert gene.path == "src/auth.py"
        assert gene.exports == ["login", "logout"]
        assert gene.is_public is True
        assert gene.is_deprecated is False

    def test_gene_equality(self):
        g1 = Gene(name="a", path="a.py")
        g2 = Gene(name="b", path="a.py")
        g3 = Gene(name="c", path="c.py")
        assert g1 == g2
        assert g1 != g3
        assert hash(g1) == hash(g2)

    def test_gene_to_dict(self):
        gene = Gene(name="m", path="m.py", lines_of_code=42)
        d = gene.to_dict()
        assert d["name"] == "m"
        assert d["lines_of_code"] == 42


class TestOperon:
    def test_operon_creation(self):
        g1 = Gene(name="a", path="a.py")
        g2 = Gene(name="b", path="b.py")
        operon = Operon(operon_id="op_0", genes=[g1, g2])
        assert operon.operon_id == "op_0"
        assert len(operon.genes) == 2

    def test_operon_polycistronic_auto(self):
        genes = [Gene(name=f"g{i}", path=f"g{i}.py") for i in range(4)]
        operon = Operon(operon_id="op_0", genes=genes)
        assert operon.polycistronic is True

    def test_operon_not_polycistronic(self):
        genes = [Gene(name="g1", path="g1.py"), Gene(name="g2", path="g2.py")]
        operon = Operon(operon_id="op_0", genes=genes)
        assert operon.polycistronic is False

    def test_operon_to_dict(self):
        operon = Operon(operon_id="op_0", genes=[Gene(name="a", path="a.py")])
        d = operon.to_dict()
        assert d["operon_id"] == "op_0"
        assert isinstance(d["genes"], list)


class TestPromoter:
    def test_promoter_creation(self):
        p = Promoter(promoter_id="p1", trigger_type="api", strength=0.8)
        assert p.strength == 0.8
        assert p.trigger_type == "api"

    def test_promoter_to_dict(self):
        p = Promoter(promoter_id="p1", trigger_type="api")
        d = p.to_dict()
        assert "promoter_id" in d


class TestRepressor:
    def test_repressor_creation(self):
        r = Repressor(
            repressor_id="r1",
            repressor_type=RepressorType.INDUCIBLE,
            repression_level=0.9,
        )
        assert r.repressor_type == RepressorType.INDUCIBLE
        assert r.repression_level == 0.9

    def test_repressor_to_dict(self):
        r = Repressor(repressor_id="r1", repressor_type=RepressorType.CONSTITUTIVE)
        d = r.to_dict()
        assert d["repressor_type"] == "constitutive"


class TestEnhancer:
    def test_enhancer_creation(self):
        e = Enhancer(
            enhancer_id="e1",
            source_gene="a.py",
            target_gene="b.py",
            enhancer_strength=0.75,
        )
        assert e.enhancer_strength == 0.75

    def test_enhancer_to_dict(self):
        e = Enhancer(enhancer_id="e1", source_gene="a.py", target_gene="b.py")
        d = e.to_dict()
        assert d["enhancer_id"] == "e1"


class TestTranscriptionFactor:
    def test_factor_creation(self):
        tf = TranscriptionFactor(
            factor_id="tf1",
            name="expert",
            factor_type=FactorType.ACTIVATOR,
            strength=0.9,
        )
        assert tf.factor_type == FactorType.ACTIVATOR
        assert tf.strength == 0.9

    def test_factor_to_dict(self):
        tf = TranscriptionFactor(factor_id="tf1", name="expert", factor_type=FactorType.REPRESSOR)
        d = tf.to_dict()
        assert d["factor_type"] == "repressor"


class TestEpigeneticMark:
    def test_mark_creation(self):
        m = EpigeneticMark(
            mark_id="m1",
            operon_id="op_0",
            mark_type=MarkType.ACETYLATION,
        )
        assert m.mark_type == MarkType.ACETYLATION
        assert m.created_at.tzinfo is not None

    def test_mark_to_dict(self):
        m = EpigeneticMark(mark_id="m1", operon_id="op_0", mark_type=MarkType.METHYLATION)
        d = m.to_dict()
        assert d["mark_type"] == "methylation"
        assert "created_at" in d


class TestCodebase:
    def test_codebase_creation(self):
        cb = Codebase(root_path="/src")
        assert cb.root_path == "/src"
        assert cb.genes == []

    def test_codebase_to_dict(self):
        cb = Codebase(root_path="/src", genes=[Gene(name="a", path="a.py")])
        d = cb.to_dict()
        assert d["root_path"] == "/src"
        assert len(d["genes"]) == 1


class TestSerializeToJson:
    def test_serialize_gene(self):
        gene = Gene(name="a", path="a.py")
        s = serialize_to_json(gene)
        assert '"name": "a"' in s

    def test_serialize_list(self):
        genes = [Gene(name="a", path="a.py"), Gene(name="b", path="b.py")]
        s = serialize_to_json(genes)
        data = json.loads(s)
        assert len(data) == 2

    def test_serialize_plain_dict(self):
        s = serialize_to_json({"key": "value"})
        assert json.loads(s)["key"] == "value"
