"""Transcription Factor Registry — conditional documentation inclusion."""

from __future__ import annotations

from operon.models import Codebase, FactorType, Gene, Operon, TranscriptionFactor


class TranscriptionFactorRegistry:
    """Manages transcription factors that control conditional documentation generation."""

    DEFAULT_FACTORS: dict[str, dict] = {
        "beginner_friendly": {
            "type": FactorType.ACTIVATOR,
            "binding_motif": ["tutorial", "example", "getting_started", "quickstart"],
            "excludes": ["advanced", "internals", "performance"],
            "coactivators_required": ["prerequisites_met"],
            "strength": 0.8,
        },
        "expert_mode": {
            "type": FactorType.ACTIVATOR,
            "binding_motif": ["internals", "performance", "edge_cases", "advanced"],
            "excludes": ["tutorial", "getting_started"],
            "corepressors_lifted": ["simplification"],
            "strength": 1.0,
        },
        "web_context": {
            "type": FactorType.ACTIVATOR,
            "binding_motif": ["http", "request", "middleware", "web", "api"],
            "conditional_expression": 'context == "web"',
            "strength": 0.9,
        },
        "embedded_context": {
            "type": FactorType.REPRESSOR,
            "binding_motif": ["http", "server", "web"],
            "repression_scope": ["web_only"],
            "strength": 0.9,
        },
        "data_science": {
            "type": FactorType.ACTIVATOR,
            "binding_motif": ["pandas", "numpy", "data", "ml", "analysis"],
            "strength": 0.7,
        },
        "cli_context": {
            "type": FactorType.ACTIVATOR,
            "binding_motif": ["argparse", "click", "command", "terminal", "cli"],
            "strength": 0.8,
        },
    }

    def __init__(self) -> None:
        self.factors: dict[str, TranscriptionFactor] = {}
        self._init_default_factors()

    def _init_default_factors(self) -> None:
        """Initialize default transcription factors."""
        for name, config in self.DEFAULT_FACTORS.items():
            factor = TranscriptionFactor(
                factor_id=f"tf_{name}",
                name=name,
                factor_type=config["type"],
                binding_motif=config.get("binding_motif", []),
                excludes=config.get("excludes", []),
                coactivators_required=config.get("coactivators_required", []),
                corepressors_lifted=config.get("corepressors_lifted", []),
                conditional_expression=config.get("conditional_expression", ""),
                repression_scope=config.get("repression_scope", []),
                strength=config.get("strength", 1.0),
            )
            self.factors[name] = factor

    def _find_web_related(self, codebase: Codebase) -> list[str]:
        """Find operons related to web functionality."""
        web_operons = []
        for operon in codebase.operons:
            for gene in operon.genes:
                if any("http" in imp or "web" in imp for imp in gene.imports):
                    web_operons.append(operon.operon_id)
                    break
        return web_operons

    def _find_web_only(self, codebase: Codebase) -> list[str]:
        """Find genes that are web-only."""
        web_only = []
        for gene in codebase.genes:
            if any("http" in imp or "web" in imp or "server" in imp for imp in gene.imports):
                if not any("data" in imp or "analysis" in imp for imp in gene.imports):
                    web_only.append(gene.path)
        return web_only

    def define_factors(self, audiences: list[str], contexts: list[str], codebase: Codebase | None = None) -> dict[str, TranscriptionFactor]:
        """Define transcription factors for given audiences and contexts."""
        factors: dict[str, TranscriptionFactor] = {}

        for audience in audiences:
            if audience in self.DEFAULT_FACTORS:
                factors[audience] = self.factors[audience]
            else:
                # Create custom factor
                factors[audience] = TranscriptionFactor(
                    factor_id=f"tf_{audience}",
                    name=audience,
                    factor_type=FactorType.ACTIVATOR,
                    binding_motif=[audience.lower()],
                    strength=0.5,
                )

        for context in contexts:
            if context in self.DEFAULT_FACTORS:
                factors[context] = self.factors[context]
            elif codebase:
                if context == "web":
                    factor = TranscriptionFactor(
                        factor_id="tf_web_context",
                        name="web_context",
                        factor_type=FactorType.ACTIVATOR,
                        binding_motif=["http", "request", "middleware"],
                        target_operons=self._find_web_related(codebase),
                        strength=0.9,
                    )
                    factors["web_context"] = factor
                else:
                    factors[context] = TranscriptionFactor(
                        factor_id=f"tf_{context}",
                        name=context,
                        factor_type=FactorType.ACTIVATOR,
                        binding_motif=[context.lower()],
                        strength=0.5,
                    )

        return factors

    def _find_matching_activators(self, gene: Gene, factors: dict[str, TranscriptionFactor], context: str) -> list[TranscriptionFactor]:
        """Find activators that match a gene."""
        activators = []
        for factor in factors.values():
            if factor.factor_type != FactorType.ACTIVATOR:
                continue
            # Check if gene matches binding motif
            for motif in factor.binding_motif:
                if motif in gene.name.lower() or motif in gene.docstring.lower():
                    # Check context if there's a conditional expression
                    if factor.conditional_expression:
                        if f'context == "{context}"' in factor.conditional_expression or context in factor.name:
                            activators.append(factor)
                    else:
                        activators.append(factor)
                    break
            # Check imports for matching motifs
            for imp in gene.imports:
                for motif in factor.binding_motif:
                    if motif in imp.lower():
                        activators.append(factor)
                        break
        return activators

    def _find_matching_repressors(self, gene: Gene, factors: dict[str, TranscriptionFactor], context: str) -> list[TranscriptionFactor]:
        """Find repressors that match a gene."""
        repressors = []
        for factor in factors.values():
            if factor.factor_type != FactorType.REPRESSOR:
                continue
            for motif in factor.binding_motif:
                if motif in gene.name.lower() or motif in gene.docstring.lower():
                    repressors.append(factor)
                    break
            for imp in gene.imports:
                for motif in factor.binding_motif:
                    if motif in imp.lower():
                        repressors.append(factor)
                        break
        return repressors

    def _calculate_expression(self, activators: list[TranscriptionFactor], repressors: list[TranscriptionFactor]) -> float:
        """Calculate net expression level from activators and repressors."""
        activation = sum(a.strength for a in activators)
        repression = sum(r.strength for r in repressors)
        net = activation - repression
        return max(0.0, min(1.0, net))

    def generate_conditional_docs(
        self, operon: Operon, factors: dict[str, TranscriptionFactor], context: str
    ) -> dict:
        """Generate documentation for an operon based on active transcription factors."""
        active_genes = []

        for gene in operon.genes:
            activators = self._find_matching_activators(gene, factors, context)
            repressors = self._find_matching_repressors(gene, factors, context)

            expression_level = self._calculate_expression(activators, repressors)

            if expression_level > 0.0:
                active_genes.append({
                    "gene": gene.to_dict(),
                    "expression_level": round(expression_level, 3),
                    "induced_by": [a.name for a in activators],
                    "repressed_by": [r.name for r in repressors],
                })

        return {
            "operon_id": operon.operon_id,
            "context": context,
            "active_genes": active_genes,
            "gene_count": len(operon.genes),
            "expressed_count": len(active_genes),
        }

    def add_custom_factor(
        self,
        name: str,
        factor_type: FactorType,
        binding_motif: list[str],
        strength: float = 1.0,
        **kwargs,
    ) -> TranscriptionFactor:
        """Add a custom transcription factor."""
        factor = TranscriptionFactor(
            factor_id=f"tf_custom_{name}",
            name=name,
            factor_type=factor_type,
            binding_motif=binding_motif,
            strength=strength,
            **kwargs,
        )
        self.factors[name] = factor
        return factor

    def get_active_factors_for_context(self, context: str) -> list[TranscriptionFactor]:
        """Get factors that are active in a specific context."""
        active = []
        for factor in self.factors.values():
            if factor.conditional_expression:
                if f'context == "{context}"' in factor.conditional_expression:
                    active.append(factor)
            elif context in factor.name or context in factor.binding_motif:
                active.append(factor)
        return active
