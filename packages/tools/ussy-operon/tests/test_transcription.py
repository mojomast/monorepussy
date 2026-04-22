"""Tests for operon.transcription module."""

import pytest

from ussy_operon.models import Codebase, FactorType, Gene, Operon
from ussy_operon.transcription import TranscriptionFactorRegistry


class TestTranscriptionFactorRegistry:
    def test_registry_creation(self):
        registry = TranscriptionFactorRegistry()
        assert len(registry.factors) > 0

    def test_default_factors(self):
        registry = TranscriptionFactorRegistry()
        assert "beginner_friendly" in registry.factors
        assert "expert_mode" in registry.factors
        assert "web_context" in registry.factors

    def test_beginner_factor_type(self):
        registry = TranscriptionFactorRegistry()
        assert registry.factors["beginner_friendly"].factor_type == FactorType.ACTIVATOR

    def test_embedded_factor_type(self):
        registry = TranscriptionFactorRegistry()
        assert registry.factors["embedded_context"].factor_type == FactorType.REPRESSOR

    def test_find_web_related(self):
        registry = TranscriptionFactorRegistry()
        g1 = Gene(name="web", path="web.py", imports=["http.server"])
        operon = Operon(operon_id="op_0", genes=[g1])
        codebase = Codebase(root_path=".", operons=[operon])
        web_operons = registry._find_web_related(codebase)
        assert "op_0" in web_operons

    def test_find_web_only(self):
        registry = TranscriptionFactorRegistry()
        g1 = Gene(name="web", path="web.py", imports=["http.server"])
        codebase = Codebase(root_path=".", genes=[g1])
        web_only = registry._find_web_only(codebase)
        assert "web.py" in web_only

    def test_define_factors_known_audience(self):
        registry = TranscriptionFactorRegistry()
        factors = registry.define_factors(audiences=["beginner"], contexts=[])
        assert "beginner" in factors

    def test_define_factors_unknown_audience(self):
        registry = TranscriptionFactorRegistry()
        factors = registry.define_factors(audiences=["custom"], contexts=[])
        assert "custom" in factors
        assert factors["custom"].factor_type == FactorType.ACTIVATOR

    def test_define_factors_web_context(self):
        registry = TranscriptionFactorRegistry()
        g1 = Gene(name="web", path="web.py", imports=["http"])
        operon = Operon(operon_id="op_0", genes=[g1])
        codebase = Codebase(root_path=".", operons=[operon])
        factors = registry.define_factors(audiences=[], contexts=["web"], codebase=codebase)
        assert "web_context" in factors or any("web" in f.name for f in factors.values())

    def test_find_matching_activators(self):
        registry = TranscriptionFactorRegistry()
        gene = Gene(name="auth", path="auth.py", docstring="authentication tutorial")
        factors = {"beginner": registry.factors["beginner_friendly"]}
        activators = registry._find_matching_activators(gene, factors, "web")
        assert len(activators) >= 1  # matches "tutorial"

    def test_find_matching_repressors(self):
        registry = TranscriptionFactorRegistry()
        gene = Gene(name="web", path="web.py", docstring="web server")
        factors = {"embedded": registry.factors["embedded_context"]}
        repressors = registry._find_matching_repressors(gene, factors, "embedded")
        assert len(repressors) >= 1  # matches "web"

    def test_calculate_expression_positive(self):
        registry = TranscriptionFactorRegistry()
        from ussy_operon.models import TranscriptionFactor
        activators = [TranscriptionFactor(factor_id="a1", name="a1", factor_type=FactorType.ACTIVATOR, strength=0.8)]
        repressors = [TranscriptionFactor(factor_id="r1", name="r1", factor_type=FactorType.REPRESSOR, strength=0.3)]
        expr = registry._calculate_expression(activators, repressors)
        assert expr == pytest.approx(0.5)

    def test_calculate_expression_zero(self):
        registry = TranscriptionFactorRegistry()
        expr = registry._calculate_expression([], [])
        assert expr == 0.0

    def test_generate_conditional_docs(self):
        registry = TranscriptionFactorRegistry()
        gene = Gene(name="auth", path="auth.py", docstring="authentication tutorial")
        operon = Operon(operon_id="op_0", genes=[gene])
        factors = registry.define_factors(audiences=["beginner"], contexts=["web"])
        result = registry.generate_conditional_docs(operon, factors, "web")
        assert result["operon_id"] == "op_0"
        assert result["context"] == "web"

    def test_generate_conditional_docs_no_match(self):
        registry = TranscriptionFactorRegistry()
        gene = Gene(name="xyz", path="xyz.py", docstring="nothing relevant")
        operon = Operon(operon_id="op_0", genes=[gene])
        factors = registry.define_factors(audiences=["beginner"], contexts=["web"])
        result = registry.generate_conditional_docs(operon, factors, "web")
        assert result["expressed_count"] == 0

    def test_add_custom_factor(self):
        registry = TranscriptionFactorRegistry()
        factor = registry.add_custom_factor(
            name="mobile",
            factor_type=FactorType.ACTIVATOR,
            binding_motif=["ios", "android"],
            strength=0.7,
        )
        assert factor.name == "mobile"
        assert factor.strength == 0.7
        assert "mobile" in registry.factors

    def test_get_active_factors_for_context(self):
        registry = TranscriptionFactorRegistry()
        active = registry.get_active_factors_for_context("web")
        assert len(active) >= 1
