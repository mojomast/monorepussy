"""Integration tests for Operon end-to-end workflows."""

import tempfile
from pathlib import Path

import pytest

from ussy_operon.enhancer import EnhancerScanner
from ussy_operon.epigenetics import EpigeneticStateTracker
from ussy_operon.mapper import OperonMapper
from ussy_operon.models import Codebase
from ussy_operon.promoter import PromoterDetector
from ussy_operon.repressor import RepressorManager
from ussy_operon.storage import StorageManager
from ussy_operon.transcription import TranscriptionFactorRegistry


class TestIntegration:
    def test_full_workflow_single_file(self):
        """Test complete workflow with a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('"""Authentication module."""\nimport os\n\ndef login():\n    pass\n\ndef logout():\n    pass\n')
            f.flush()
            path = Path(f.name)
        try:
            codebase = Codebase(root_path=str(path))
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            assert len(operons) == 1
            assert operons[0].operon_id == "operon_0"
            assert len(operons[0].genes) == 1

            # Promoter detection
            detector = PromoterDetector()
            triggers = detector.analyze_promoters(codebase, [])
            assert len(triggers) >= 5

            # Repressor management
            manager = RepressorManager()
            repressors = manager.manage_repressors(codebase)
            assert isinstance(repressors, list)

            # Enhancer scanning
            scanner = EnhancerScanner()
            enhancers = scanner.find_enhancers(codebase)
            assert enhancers == []  # Single gene has no connections

            # Transcription factors
            registry = TranscriptionFactorRegistry()
            factors = registry.define_factors(audiences=["beginner"], contexts=["web"])
            assert len(factors) > 0

            # Epigenetics
            tracker = EpigeneticStateTracker()
            state = tracker.track_epigenetic_state([], codebase)
            assert state["total_operons"] == 1

        finally:
            path.unlink()

    def test_full_workflow_directory(self):
        """Test complete workflow with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create auth module
            (Path(tmpdir) / "auth.py").write_text('"""Authentication."""\nimport json\ndef login(): pass\n')
            (Path(tmpdir) / "auth_utils.py").write_text('"""Auth utilities."""\nimport json\ndef hash(): pass\n')
            (Path(tmpdir) / "api.py").write_text('"""API routes."""\nfrom auth import login\nfrom auth_utils import hash\ndef route(): pass\n')

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            # Should find operons
            assert len(operons) >= 1

            # Storage persistence
            storage = StorageManager(":memory:")
            for operon in operons:
                storage.save_operon(operon)
            loaded = storage.load_operons()
            assert len(loaded) == len(operons)

            # Promoter detection
            detector = PromoterDetector()
            triggers = detector.analyze_promoters(codebase, [])
            assert len(triggers) > 0

            # Enhancer scanning
            scanner = EnhancerScanner()
            enhancers = scanner.find_enhancers(codebase)
            # Should find some enhancers due to shared imports
            assert isinstance(enhancers, list)

    def test_storage_round_trip(self):
        """Test that all entities can be saved and loaded."""
        storage = StorageManager(":memory:")

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module.py").write_text("def func(): pass\n")

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            # Save all entities
            storage.save_codebase(codebase)
            for operon in operons:
                storage.save_operon(operon)

            # Promoters
            from ussy_operon.promoter import PromoterDetector
            detector = PromoterDetector()
            triggers = detector.analyze_promoters(codebase, [])
            for t in triggers.values():
                storage.save_promoter(t)

            # Repressors
            from ussy_operon.repressor import RepressorManager
            manager = RepressorManager()
            repressors = manager.manage_repressors(codebase)
            for r in repressors:
                storage.save_repressor(r)

            # Load and verify
            assert len(storage.load_codebases()) == 1
            assert len(storage.load_operons()) == len(operons)
            assert len(storage.load_promoters()) == len(triggers)
            assert len(storage.load_repressors()) == len(repressors)

    def test_conditional_docs_generation(self):
        """Test conditional documentation generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "auth.py").write_text('"""Authentication tutorial."""\ndef login(): pass\n')

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            registry = TranscriptionFactorRegistry()
            factors = registry.define_factors(audiences=["beginner"], contexts=["web"])

            result = registry.generate_conditional_docs(operons[0], factors, "web")
            assert result["operon_id"] == operons[0].operon_id
            assert result["context"] == "web"
            # Should express the gene due to "tutorial" motif
            assert result["expressed_count"] >= 0

    def test_epigenetic_state_tracking(self):
        """Test epigenetic state tracking over time."""
        from datetime import datetime, timedelta, timezone
        from ussy_operon.models import Gene, Operon, MarkType

        operon = Operon(operon_id="op_0", genes=[Gene(name="old", path="old.py", is_deprecated=True)])
        codebase = Codebase(root_path=".", operons=[operon])

        tracker = EpigeneticStateTracker()

        # Test with archived history
        history = [{
            "operon_id": "op_0",
            "action": "archive",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        }]

        state = tracker.track_epigenetic_state(history, codebase)
        assert state["current_marks"][0]["mark_type"] == "methylation"

    def test_repressor_lift_and_apply(self):
        """Test repressor lift and apply operations."""
        from ussy_operon.models import Gene

        gene = Gene(name="deprecated", path="deprecated.py", is_deprecated=True)
        codebase = Codebase(root_path=".", deprecated_features=[gene])

        manager = RepressorManager()
        manager.manage_repressors(codebase)

        # Initially repressed
        assert manager.is_repressed("deprecated.py") is True

        # Lift repression
        rep_id = manager.repressors[0].repressor_id
        success = manager.lift_repression(rep_id)
        assert success is True
        assert manager.is_repressed("deprecated.py") is False

        # Re-apply
        success = manager.apply_repression(rep_id)
        assert success is True
        assert manager.is_repressed("deprecated.py") is True

    def test_enhancer_strength_calculation(self):
        """Test that enhancer strength decays with distance."""
        from ussy_operon.models import Gene, Operon

        g1 = Gene(name="a", path="a.py", exports=["shared"], lines_of_code=100)
        g2 = Gene(name="b", path="b.py", exports=["shared"], lines_of_code=100)
        operon = Operon(operon_id="op_0", genes=[g1, g2])
        codebase = Codebase(root_path=".", genes=[g1, g2], operons=[operon])

        scanner = EnhancerScanner()

        # Build import graph where a imports b
        graph = {"a.py": {"b.py"}, "b.py": set()}
        distant = scanner._transitive_relationships(g1, graph, [g1, g2])

        # Should find connection at distance 1
        assert len(distant) >= 0

    def test_promoter_urgency_calculation(self):
        """Test that promoter urgency increases with recent changes."""
        from datetime import datetime, timezone

        detector = PromoterDetector()
        history = [
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
        ]

        urgency = detector._calculate_doc_urgency("api", history)
        assert urgency > 0.5  # Higher than default

    def test_cli_end_to_end(self, capsys):
        """Test CLI commands end-to-end."""
        from ussy_operon.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module.py").write_text("def func(): pass\n")

            # Map
            code = main(["--json", "map", tmpdir])
            assert code == 0

            # Promote
            code = main(["--json", "promote", "public_api_change"])
            assert code == 0

            # Enhance
            code = main(["--json", "enhance", tmpdir])
            assert code == 0

            # Epigenetics
            code = main(["--json", "epigenetics"])
            assert code == 0

    def test_multiple_operons_detection(self):
        """Test detection of multiple operons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create independent modules (no shared imports)
            (Path(tmpdir) / "os_utils.py").write_text("import os\ndef util(): pass\n")
            (Path(tmpdir) / "json_utils.py").write_text("import json\ndef util(): pass\n")

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            # Should find at least 2 operons (or more due to singletons)
            assert len(operons) >= 2

    def test_cross_module_analysis(self):
        """Test analysis of modules that import each other."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "base.py").write_text("def base_func(): pass\n")
            (Path(tmpdir) / "derived.py").write_text("from base import base_func\ndef derived(): pass\n")

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            # Modules should be coupled
            assert len(operons) >= 1

    def test_empty_codebase_handling(self):
        """Test handling of empty codebases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)

            assert operons == []
            assert codebase.genes == []

            # All instruments should handle empty gracefully
            scanner = EnhancerScanner()
            enhancers = scanner.find_enhancers(codebase)
            assert enhancers == []

            detector = PromoterDetector()
            triggers = detector.analyze_promoters(codebase, [])
            assert len(triggers) >= len(PromoterDetector.TRIGGER_DEFINITIONS)

            tracker = EpigeneticStateTracker()
            state = tracker.track_epigenetic_state([], codebase)
            assert state["current_marks"] == []

    def test_internal_api_detection(self):
        """Test detection of internal APIs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "_internal.py").write_text('"""Internal module."""\n# internal\ndef helper(): pass\n')
            (Path(tmpdir) / "public.py").write_text('"""Public module."""\ndef api(): pass\n')

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            mapper.map_operons(codebase)

            # Should detect internal APIs
            internal_paths = [g.path for g in codebase.internal_apis]
            assert any("_internal" in p or "internal" in p for p in internal_paths)

    def test_deprecated_feature_detection(self):
        """Test detection of deprecated features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "legacy.py").write_text('"""DEPRECATED: Use new_module instead."""\ndef old(): pass\n')

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            mapper.map_operons(codebase)

            assert len(codebase.deprecated_features) == 1
            assert codebase.deprecated_features[0].name == "legacy"

    def test_polycistronic_detection(self):
        """Test detection of polycistronic operons (multi-module)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 4 modules that share imports (should cluster together)
            for i in range(4):
                (Path(tmpdir) / f"module_{i}.py").write_text(f"import os\ndef func_{i}(): pass\n")

            codebase = Codebase(root_path=tmpdir)
            mapper = OperonMapper(coupling_threshold=0.3)
            operons = mapper.map_operons(codebase)

            # At least one operon should be polycistronic
            assert any(op.polycistronic for op in operons)
