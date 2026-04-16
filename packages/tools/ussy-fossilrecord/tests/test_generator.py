"""Tests for the Living Fossil generator."""
from __future__ import annotations

import json
import pytest

from fossilrecord.corpus.loader import StressCategory
from fossilrecord.generator.living_fossil import (
    LivingFossilGenerator,
    GenerationConfig,
    EmbeddedProgram,
)


class TestGenerationConfig:
    """Tests for GenerationConfig."""

    def test_default_config(self):
        config = GenerationConfig()
        assert config.count == 10
        assert config.seed is None
        assert len(config.host_languages) >= 5
        assert "python" in config.host_languages

    def test_custom_config(self):
        config = GenerationConfig(count=50, seed=42, host_languages=["python"])
        assert config.count == 50
        assert config.seed == 42
        assert config.host_languages == ["python"]

    def test_to_dict(self):
        config = GenerationConfig(count=5)
        d = config.to_dict()
        assert d["count"] == 5
        assert "host_languages" in d


class TestEmbeddedProgram:
    """Tests for EmbeddedProgram dataclass."""

    def test_create_embedded_program(self):
        ep = EmbeddedProgram(
            name="test_embed",
            host_language="python",
            esolang="Brainfuck",
            source="# +++.\nprint('ok')",
            embedding_type="comment",
        )
        assert ep.host_language == "python"
        assert ep.esolang == "Brainfuck"

    def test_to_dict(self):
        ep = EmbeddedProgram(
            name="test",
            host_language="python",
            esolang="BF",
            source="x",
            embedding_type="string",
            categories=[StressCategory.CONCISE],
        )
        d = ep.to_dict()
        assert d["name"] == "test"
        assert "concise" in d["categories"]


class TestLivingFossilGenerator:
    """Tests for LivingFossilGenerator."""

    def test_generate_default(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=5, seed=42))
        results = gen.generate()
        assert len(results) == 5

    def test_generate_deterministic_with_seed(self):
        gen1 = LivingFossilGenerator(config=GenerationConfig(count=10, seed=123))
        gen2 = LivingFossilGenerator(config=GenerationConfig(count=10, seed=123))
        r1 = gen1.generate()
        r2 = gen2.generate()
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.name == b.name
            assert a.source == b.source

    def test_generate_different_with_different_seed(self):
        gen1 = LivingFossilGenerator(config=GenerationConfig(count=10, seed=1))
        gen2 = LivingFossilGenerator(config=GenerationConfig(count=10, seed=2))
        r1 = gen1.generate()
        r2 = gen2.generate()
        # At least some should differ
        names1 = {r.name for r in r1}
        names2 = {r.name for r in r2}
        assert names1 != names2

    def test_generate_has_embedding_types(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=20, seed=42))
        results = gen.generate()
        embed_types = {r.embedding_type for r in results}
        assert len(embed_types) >= 2  # Should have variety

    def test_generate_has_host_languages(self):
        gen = LivingFossilGenerator(
            config=GenerationConfig(count=20, seed=42, host_languages=["python", "javascript"])
        )
        results = gen.generate()
        hosts = {r.host_language for r in results}
        # Should have at least one host language
        assert len(hosts) >= 1

    def test_generate_for_category(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=5, seed=42))
        results = gen.generate_for_category(StressCategory.WHITESPACE, count=5)
        assert len(results) >= 1

    def test_generate_count_override(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=5, seed=42))
        results = gen.generate(count=3)
        assert len(results) == 3

    def test_generate_large_count(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=100, seed=42))
        results = gen.generate()
        assert len(results) == 100

    def test_embedded_in_python_comment(self):
        gen = LivingFossilGenerator(config=GenerationConfig(count=1, seed=42, host_languages=["python"]))
        from fossilrecord.corpus.loader import EsolangProgram
        prog = EsolangProgram("test", "BF", "+++.", "", [StressCategory.MINIMALISTIC], 1)
        results = gen._generate_embedded([prog], 1)
        assert len(results) == 1
        # Could be any embedding type (comment, string, or literal)
        assert results[0].host_language == "python"

    def test_extreme_nesting(self):
        gen = LivingFossilGenerator(config=GenerationConfig(
            count=1, seed=42, extreme_nesting_depth=10
        ))
        source = gen._extreme_nesting()
        # Should have 10 levels of if True:
        assert source.count("if True:") == 10
        assert "pass" in source

    def test_extreme_line_length(self):
        gen = LivingFossilGenerator(config=GenerationConfig(
            count=1, seed=42, extreme_line_length=500
        ))
        source = gen._extreme_line_length()
        lines = source.split("\n")
        long_lines = [l for l in lines if len(l) > 200]
        assert len(long_lines) >= 1

    def test_extreme_symbol_density(self):
        gen = LivingFossilGenerator(config=GenerationConfig(
            count=1, seed=42, symbol_density_count=100
        ))
        source = gen._extreme_symbol_density()
        assert "Symbol-dense" in source

    def test_chimera_generation(self):
        from fossilrecord.corpus.loader import EsolangProgram
        progs = [
            EsolangProgram("p1", "Brainfuck", "+++.", "", [StressCategory.MINIMALISTIC], 1),
            EsolangProgram("p2", "Befunge-93", "0\"!\":v", "", [StressCategory.TWOD], 2),
        ]
        gen = LivingFossilGenerator(config=GenerationConfig(count=1, seed=42))
        results = gen._generate_chimeras(progs, 1)
        assert len(results) == 1
        assert results[0].embedding_type == "chimera"
