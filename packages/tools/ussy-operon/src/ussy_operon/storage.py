"""SQLite storage backend for Operon."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

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
)


class StorageManager:
    """Manages SQLite storage for all Operon entities."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._connection: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _init_db(self) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operons (
                operon_id TEXT PRIMARY KEY,
                genes TEXT NOT NULL,
                promoter_region TEXT NOT NULL,
                operator_sites TEXT NOT NULL,
                polycistronic INTEGER NOT NULL,
                regulatory_proteins TEXT NOT NULL,
                coupling_score REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promoters (
                promoter_id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                strength REAL NOT NULL,
                rnap_binding TEXT NOT NULL,
                transcription_rate TEXT,
                target_operon TEXT NOT NULL,
                sigma_factor TEXT NOT NULL,
                upstream_activators TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repressors (
                repressor_id TEXT PRIMARY KEY,
                repressor_type TEXT NOT NULL,
                operator_site TEXT NOT NULL,
                repressor_protein TEXT NOT NULL,
                inducer TEXT NOT NULL,
                corepressor TEXT NOT NULL,
                allosteric_state TEXT NOT NULL,
                repression_level REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enhancers (
                enhancer_id TEXT PRIMARY KEY,
                source_gene TEXT NOT NULL,
                target_gene TEXT NOT NULL,
                target_operon TEXT NOT NULL,
                distance_kb REAL NOT NULL,
                orientation TEXT NOT NULL,
                enhancer_strength REAL NOT NULL,
                transcription_factors_required TEXT NOT NULL,
                tissue_specificity TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcription_factors (
                factor_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                factor_type TEXT NOT NULL,
                binding_motif TEXT NOT NULL,
                target_operons TEXT NOT NULL,
                excludes TEXT NOT NULL,
                coactivators_required TEXT NOT NULL,
                corepressors_lifted TEXT NOT NULL,
                conditional_expression TEXT NOT NULL,
                repression_scope TEXT NOT NULL,
                strength REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epigenetic_marks (
                mark_id TEXT PRIMARY KEY,
                operon_id TEXT NOT NULL,
                mark_type TEXT NOT NULL,
                position TEXT NOT NULL,
                inheritance TEXT NOT NULL,
                effect TEXT NOT NULL,
                level REAL NOT NULL,
                deacetylase_risk INTEGER NOT NULL,
                change TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS codebases (
                root_path TEXT PRIMARY KEY,
                genes TEXT NOT NULL,
                operons TEXT NOT NULL,
                deprecated_features TEXT NOT NULL,
                internal_apis TEXT NOT NULL
            )
        """)

        conn.commit()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def _encode_list(self, data: list[Any]) -> str:
        return json.dumps(data)

    def _decode_list(self, data: str) -> list[Any]:
        return json.loads(data)

    def save_operon(self, operon: Operon) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO operons
            (operon_id, genes, promoter_region, operator_sites, polycistronic,
             regulatory_proteins, coupling_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                operon.operon_id,
                self._encode_list([g.to_dict() for g in operon.genes]),
                self._encode_list(operon.promoter_region),
                self._encode_list(operon.operator_sites),
                int(operon.polycistronic),
                self._encode_list(operon.regulatory_proteins),
                operon.coupling_score,
            ),
        )
        conn.commit()

    def load_operons(self) -> list[Operon]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operons")
        rows = cursor.fetchall()
        operons = []
        for row in rows:
            genes = [Gene(**g) for g in self._decode_list(row["genes"])]
            operons.append(
                Operon(
                    operon_id=row["operon_id"],
                    genes=genes,
                    promoter_region=self._decode_list(row["promoter_region"]),
                    operator_sites=self._decode_list(row["operator_sites"]),
                    polycistronic=bool(row["polycistronic"]),
                    regulatory_proteins=self._decode_list(row["regulatory_proteins"]),
                    coupling_score=row["coupling_score"],
                )
            )
        return operons

    def delete_operon(self, operon_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM operons WHERE operon_id = ?", (operon_id,))
        conn.commit()

    def save_promoter(self, promoter: Promoter) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO promoters
            (promoter_id, trigger_type, strength, rnap_binding, transcription_rate,
             target_operon, sigma_factor, upstream_activators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                promoter.promoter_id,
                promoter.trigger_type,
                promoter.strength,
                self._encode_list(promoter.rnap_binding),
                json.dumps(promoter.transcription_rate),
                promoter.target_operon,
                self._encode_list(promoter.sigma_factor),
                self._encode_list(promoter.upstream_activators),
            ),
        )
        conn.commit()

    def load_promoters(self) -> list[Promoter]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promoters")
        rows = cursor.fetchall()
        promoters = []
        for row in rows:
            tr = row["transcription_rate"]
            try:
                transcription_rate = json.loads(tr)
            except (json.JSONDecodeError, TypeError):
                transcription_rate = tr
            promoters.append(
                Promoter(
                    promoter_id=row["promoter_id"],
                    trigger_type=row["trigger_type"],
                    strength=row["strength"],
                    rnap_binding=self._decode_list(row["rnap_binding"]),
                    transcription_rate=transcription_rate,
                    target_operon=row["target_operon"],
                    sigma_factor=self._decode_list(row["sigma_factor"]),
                    upstream_activators=self._decode_list(row["upstream_activators"]),
                )
            )
        return promoters

    def delete_promoter(self, promoter_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM promoters WHERE promoter_id = ?", (promoter_id,))
        conn.commit()

    def save_repressor(self, repressor: Repressor) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO repressors
            (repressor_id, repressor_type, operator_site, repressor_protein,
             inducer, corepressor, allosteric_state, repression_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repressor.repressor_id,
                repressor.repressor_type.value,
                repressor.operator_site,
                repressor.repressor_protein,
                repressor.inducer,
                repressor.corepressor,
                repressor.allosteric_state,
                repressor.repression_level,
            ),
        )
        conn.commit()

    def load_repressors(self) -> list[Repressor]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM repressors")
        rows = cursor.fetchall()
        repressors = []
        for row in rows:
            repressors.append(
                Repressor(
                    repressor_id=row["repressor_id"],
                    repressor_type=RepressorType(row["repressor_type"]),
                    operator_site=row["operator_site"],
                    repressor_protein=row["repressor_protein"],
                    inducer=row["inducer"],
                    corepressor=row["corepressor"],
                    allosteric_state=row["allosteric_state"],
                    repression_level=row["repression_level"],
                )
            )
        return repressors

    def delete_repressor(self, repressor_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repressors WHERE repressor_id = ?", (repressor_id,))
        conn.commit()

    def save_enhancer(self, enhancer: Enhancer) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO enhancers
            (enhancer_id, source_gene, target_gene, target_operon, distance_kb,
             orientation, enhancer_strength, transcription_factors_required, tissue_specificity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                enhancer.enhancer_id,
                enhancer.source_gene,
                enhancer.target_gene,
                enhancer.target_operon,
                enhancer.distance_kb,
                enhancer.orientation,
                enhancer.enhancer_strength,
                self._encode_list(enhancer.transcription_factors_required),
                self._encode_list(enhancer.tissue_specificity),
            ),
        )
        conn.commit()

    def load_enhancers(self) -> list[Enhancer]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enhancers")
        rows = cursor.fetchall()
        enhancers = []
        for row in rows:
            enhancers.append(
                Enhancer(
                    enhancer_id=row["enhancer_id"],
                    source_gene=row["source_gene"],
                    target_gene=row["target_gene"],
                    target_operon=row["target_operon"],
                    distance_kb=row["distance_kb"],
                    orientation=row["orientation"],
                    enhancer_strength=row["enhancer_strength"],
                    transcription_factors_required=self._decode_list(row["transcription_factors_required"]),
                    tissue_specificity=self._decode_list(row["tissue_specificity"]),
                )
            )
        return enhancers

    def delete_enhancer(self, enhancer_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM enhancers WHERE enhancer_id = ?", (enhancer_id,))
        conn.commit()

    def save_transcription_factor(self, factor: TranscriptionFactor) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO transcription_factors
            (factor_id, name, factor_type, binding_motif, target_operons, excludes,
             coactivators_required, corepressors_lifted, conditional_expression,
             repression_scope, strength)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                factor.factor_id,
                factor.name,
                factor.factor_type.value,
                self._encode_list(factor.binding_motif),
                self._encode_list(factor.target_operons),
                self._encode_list(factor.excludes),
                self._encode_list(factor.coactivators_required),
                self._encode_list(factor.corepressors_lifted),
                factor.conditional_expression,
                self._encode_list(factor.repression_scope),
                factor.strength,
            ),
        )
        conn.commit()

    def load_transcription_factors(self) -> list[TranscriptionFactor]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transcription_factors")
        rows = cursor.fetchall()
        factors = []
        for row in rows:
            factors.append(
                TranscriptionFactor(
                    factor_id=row["factor_id"],
                    name=row["name"],
                    factor_type=FactorType(row["factor_type"]),
                    binding_motif=self._decode_list(row["binding_motif"]),
                    target_operons=self._decode_list(row["target_operons"]),
                    excludes=self._decode_list(row["excludes"]),
                    coactivators_required=self._decode_list(row["coactivators_required"]),
                    corepressors_lifted=self._decode_list(row["corepressors_lifted"]),
                    conditional_expression=row["conditional_expression"],
                    repression_scope=self._decode_list(row["repression_scope"]),
                    strength=row["strength"],
                )
            )
        return factors

    def delete_transcription_factor(self, factor_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transcription_factors WHERE factor_id = ?", (factor_id,))
        conn.commit()

    def save_epigenetic_mark(self, mark: EpigeneticMark) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO epigenetic_marks
            (mark_id, operon_id, mark_type, position, inheritance, effect, level,
             deacetylase_risk, change, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mark.mark_id,
                mark.operon_id,
                mark.mark_type.value,
                mark.position,
                mark.inheritance,
                mark.effect,
                mark.level,
                int(mark.deacetylase_risk),
                mark.change,
                mark.created_at.isoformat(),
            ),
        )
        conn.commit()

    def load_epigenetic_marks(self) -> list[EpigeneticMark]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM epigenetic_marks")
        rows = cursor.fetchall()
        marks = []
        for row in rows:
            from datetime import datetime

            marks.append(
                EpigeneticMark(
                    mark_id=row["mark_id"],
                    operon_id=row["operon_id"],
                    mark_type=MarkType(row["mark_type"]),
                    position=row["position"],
                    inheritance=row["inheritance"],
                    effect=row["effect"],
                    level=row["level"],
                    deacetylase_risk=bool(row["deacetylase_risk"]),
                    change=row["change"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return marks

    def delete_epigenetic_mark(self, mark_id: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM epigenetic_marks WHERE mark_id = ?", (mark_id,))
        conn.commit()

    def save_codebase(self, codebase: Codebase) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO codebases
            (root_path, genes, operons, deprecated_features, internal_apis)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                codebase.root_path,
                self._encode_list([g.to_dict() for g in codebase.genes]),
                self._encode_list([o.to_dict() for o in codebase.operons]),
                self._encode_list([g.to_dict() for g in codebase.deprecated_features]),
                self._encode_list([g.to_dict() for g in codebase.internal_apis]),
            ),
        )
        conn.commit()

    def load_codebases(self) -> list[Codebase]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM codebases")
        rows = cursor.fetchall()
        codebases = []
        for row in rows:
            genes = [Gene(**g) for g in self._decode_list(row["genes"])]
            operons = []
            for o in self._decode_list(row["operons"]):
                o_genes = [Gene(**g) for g in o.get("genes", [])]
                operons.append(
                    Operon(
                        operon_id=o["operon_id"],
                        genes=o_genes,
                        promoter_region=o.get("promoter_region", []),
                        operator_sites=o.get("operator_sites", []),
                        polycistronic=o.get("polycistronic", False),
                        regulatory_proteins=o.get("regulatory_proteins", []),
                        coupling_score=o.get("coupling_score", 0.0),
                    )
                )
            deprecated = [Gene(**g) for g in self._decode_list(row["deprecated_features"])]
            internal = [Gene(**g) for g in self._decode_list(row["internal_apis"])]
            codebases.append(
                Codebase(
                    root_path=row["root_path"],
                    genes=genes,
                    operons=operons,
                    deprecated_features=deprecated,
                    internal_apis=internal,
                )
            )
        return codebases

    def clear_all(self) -> None:
        """Clear all data from all tables."""
        conn = self._get_conn()
        cursor = conn.cursor()
        for table in [
            "operons",
            "promoters",
            "repressors",
            "enhancers",
            "transcription_factors",
            "epigenetic_marks",
            "codebases",
        ]:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
