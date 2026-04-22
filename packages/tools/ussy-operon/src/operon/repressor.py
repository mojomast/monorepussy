"""Repressor Manager — manages deprecation and suppression of documentation."""

from __future__ import annotations

from operon.models import Codebase, Gene, Repressor, RepressorType


class RepressorManager:
    """Manages what documentation should be suppressed and when."""

    def __init__(self) -> None:
        self.repressors: list[Repressor] = []

    def _create_laci_repressor(self, feature: Gene) -> Repressor:
        """Create a LacI-type repressor (inducible, active by default for deprecated features)."""
        return Repressor(
            repressor_id=f"rep_laci_{feature.name}",
            repressor_type=RepressorType.INDUCIBLE,
            operator_site=feature.path,
            repressor_protein=f"Rep_{feature.name}",
            inducer="maintainer_override",
            allosteric_state="active" if feature.is_deprecated else "inactive",
            repression_level=1.0 if feature.is_deprecated else 0.0,
        )

    def _create_trpr_repressor(self, feature: Gene) -> Repressor:
        """Create a TrpR-type repressor (corepressor-dependent, active for internal APIs)."""
        return Repressor(
            repressor_id=f"rep_trpr_{feature.name}",
            repressor_type=RepressorType.COREPRESSOR_DEPENDENT,
            operator_site=feature.path,
            repressor_protein="Rep_internal",
            corepressor="@internal_tag",
            allosteric_state="active",
            repression_level=1.0,
        )

    def _create_constitutive_repressor(self, feature: Gene) -> Repressor:
        """Create a constitutive repressor (always active for private utilities)."""
        return Repressor(
            repressor_id=f"rep_const_{feature.name}",
            repressor_type=RepressorType.CONSTITUTIVE,
            operator_site=feature.path,
            repressor_protein="Rep_private",
            allosteric_state="active",
            repression_level=1.0,
        )

    def manage_repressors(self, codebase: Codebase) -> list[Repressor]:
        """Manage repressors for all features in the codebase."""
        repressors: list[Repressor] = []

        # LacI-type: deprecated features
        for feature in codebase.deprecated_features:
            repressors.append(self._create_laci_repressor(feature))

        # TrpR-type: internal APIs
        for feature in codebase.internal_apis:
            repressors.append(self._create_trpr_repressor(feature))

        # Constitutive: private modules (start with underscore)
        for gene in codebase.genes:
            if gene.name.startswith("_") and not gene.is_internal:
                repressors.append(self._create_constitutive_repressor(gene))

        self.repressors = repressors
        return repressors

    def lift_repression(self, repressor_id: str, inducer: str = "") -> bool:
        """Lift repression on a specific repressor (e.g., for migration guides)."""
        for rep in self.repressors:
            if rep.repressor_id == repressor_id:
                if rep.repressor_type == RepressorType.INDUCIBLE and (not inducer or rep.inducer == inducer):
                    rep.allosteric_state = "inactive"
                    rep.repression_level = 0.0
                    return True
                elif rep.repressor_type == RepressorType.COREPRESSOR_DEPENDENT and inducer == rep.corepressor:
                    rep.allosteric_state = "inactive"
                    rep.repression_level = 0.0
                    return True
        return False

    def apply_repression(self, repressor_id: str) -> bool:
        """Re-apply repression to a specific repressor."""
        for rep in self.repressors:
            if rep.repressor_id == repressor_id:
                rep.allosteric_state = "active"
                rep.repression_level = 1.0
                return True
        return False

    def is_repressed(self, feature_path: str) -> bool:
        """Check if a feature path is currently repressed."""
        for rep in self.repressors:
            if rep.operator_site == feature_path and rep.repression_level > 0.5:
                return True
        return False

    def get_repression_level(self, feature_path: str) -> float:
        """Get the aggregate repression level for a feature path."""
        levels = [rep.repression_level for rep in self.repressors if rep.operator_site == feature_path]
        return max(levels) if levels else 0.0

    def filter_visible_genes(self, genes: list[Gene]) -> list[Gene]:
        """Filter genes to only those that are not repressed."""
        return [g for g in genes if not self.is_repressed(g.path)]

    def add_custom_repressor(
        self,
        feature_path: str,
        repressor_type: RepressorType,
        repression_level: float = 1.0,
        inducer: str = "",
        corepressor: str = "",
    ) -> Repressor:
        """Add a custom repressor for a feature."""
        sanitized = feature_path.replace("/", "_").replace("\\", "_")
        rep = Repressor(
            repressor_id=f"rep_custom_{sanitized}",
            repressor_type=repressor_type,
            operator_site=feature_path,
            repressor_protein="Rep_custom",
            inducer=inducer,
            corepressor=corepressor,
            allosteric_state="active",
            repression_level=repression_level,
        )
        self.repressors.append(rep)
        return rep
