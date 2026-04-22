"""Tests for operon.promoter module."""

from datetime import datetime, timezone

import pytest

from ussy_operon.models import Codebase, Gene, Operon, Promoter
from ussy_operon.promoter import PromoterDetector


class TestPromoterDetector:
    def test_detector_creation(self):
        detector = PromoterDetector()
        assert detector.triggers == {}

    def test_trigger_definitions(self):
        assert "public_api_change" in PromoterDetector.TRIGGER_DEFINITIONS
        assert PromoterDetector.TRIGGER_DEFINITIONS["public_api_change"]["strength"] == 1.0

    def test_calculate_doc_urgency_empty(self):
        detector = PromoterDetector()
        urgency = detector._calculate_doc_urgency("api", [])
        assert urgency == 0.5

    def test_calculate_doc_urgency_with_history(self):
        detector = PromoterDetector()
        history = [
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"type": "api", "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        urgency = detector._calculate_doc_urgency("api", history)
        assert urgency > 0.5
        assert urgency <= 1.0

    def test_find_specialized_triggers_polycistronic(self):
        detector = PromoterDetector()
        operon = Operon(operon_id="op_0", genes=[Gene(name=f"g{i}", path=f"g{i}.py") for i in range(5)])
        triggers = detector._find_specialized_triggers(operon)
        assert "large_operon_change" in triggers

    def test_find_specialized_triggers_deprecated(self):
        detector = PromoterDetector()
        operon = Operon(operon_id="op_0", genes=[Gene(name="g", path="g.py", is_deprecated=True)])
        triggers = detector._find_specialized_triggers(operon)
        assert "deprecated_feature" in triggers

    def test_find_specialized_triggers_internal(self):
        detector = PromoterDetector()
        operon = Operon(operon_id="op_0", genes=[Gene(name="g", path="g.py", is_internal=True)])
        triggers = detector._find_specialized_triggers(operon)
        assert "internal_api" in triggers

    def test_find_prerequisites(self):
        detector = PromoterDetector()
        operon = Operon(
            operon_id="op_0",
            genes=[Gene(name="g", path="g.py", docstring="Has docs")],
            regulatory_proteins=["os"],
            coupling_score=0.9,
        )
        prereqs = detector._find_prerequisites(operon)
        assert "dependencies_documented" in prereqs
        assert "has_documentation" in prereqs
        assert "high_coupling" in prereqs

    def test_analyze_promoters_basic(self):
        detector = PromoterDetector()
        codebase = Codebase(root_path=".", genes=[], operons=[])
        triggers = detector.analyze_promoters(codebase, history=[])
        assert len(triggers) >= len(PromoterDetector.TRIGGER_DEFINITIONS)

    def test_analyze_promoters_with_operon(self):
        detector = PromoterDetector()
        operon = Operon(operon_id="op_0", genes=[Gene(name="g", path="g.py")])
        codebase = Codebase(root_path=".", operons=[operon])
        triggers = detector.analyze_promoters(codebase, history=[])
        assert "op_0" in triggers

    def test_get_promoter_strength_known(self):
        detector = PromoterDetector()
        detector.triggers = {"api": Promoter(promoter_id="p1", trigger_type="api", strength=0.8)}
        assert detector.get_promoter_strength("api") == 0.8

    def test_get_promoter_strength_unknown(self):
        detector = PromoterDetector()
        assert detector.get_promoter_strength("unknown") == 0.0

    def test_should_generate_true(self):
        detector = PromoterDetector()
        detector.triggers = {"api": Promoter(promoter_id="p1", trigger_type="api", strength=0.8)}
        assert detector.should_generate("api", min_strength=0.5) is True

    def test_should_generate_false(self):
        detector = PromoterDetector()
        detector.triggers = {"api": Promoter(promoter_id="p1", trigger_type="api", strength=0.3)}
        assert detector.should_generate("api", min_strength=0.5) is False

    def test_get_priority_order(self):
        detector = PromoterDetector()
        detector.triggers = {
            "low": Promoter(promoter_id="p1", trigger_type="low", strength=0.2),
            "high": Promoter(promoter_id="p2", trigger_type="high", strength=0.9),
            "mid": Promoter(promoter_id="p3", trigger_type="mid", strength=0.5),
        }
        order = detector.get_priority_order()
        assert order[0][0] == "high"
        assert order[-1][0] == "low"
