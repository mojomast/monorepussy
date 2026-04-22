"""Tests for fault line detection."""
import pytest
from ussy_stratax.models import BedrockReport, FaultLine
from ussy_stratax.analysis.faults import FaultLineDetector


class TestFaultLineDetector:
    def setup_method(self):
        self.detector = FaultLineDetector()

    def test_no_faults_same_stability(self):
        reports = [
            BedrockReport("pkg", "fn1", 85.0, 8, 10, 2.0),
            BedrockReport("pkg", "fn2", 80.0, 8, 10, 1.5),
        ]
        faults = self.detector.detect("pkg", reports)
        assert len(faults) == 0

    def test_fault_line_detected(self):
        reports = [
            BedrockReport("pkg", "stable_fn", 95.0, 9, 10, 3.0),
            BedrockReport("pkg", "unstable_fn", 20.0, 2, 10, 0.0),
        ]
        faults = self.detector.detect("pkg", reports)
        assert len(faults) == 1
        assert faults[0].bedrock_function == "stable_fn"
        assert faults[0].unstable_function == "unstable_fn"
        assert faults[0].bedrock_score == 95.0
        assert faults[0].unstable_score == 20.0

    def test_custom_threshold(self):
        detector = FaultLineDetector(score_gap_threshold=20.0)
        reports = [
            BedrockReport("pkg", "fn1", 70.0, 7, 10, 1.0),
            BedrockReport("pkg", "fn2", 45.0, 4, 10, 0.5),
        ]
        faults = detector.detect("pkg", reports)
        # Gap is 25, which exceeds threshold of 20
        assert len(faults) == 1

    def test_multiple_functions(self):
        reports = [
            BedrockReport("pkg", "bedrock_fn", 95.0, 9, 10, 3.0),
            BedrockReport("pkg", "stable_fn", 70.0, 7, 10, 1.0),
            BedrockReport("pkg", "quicksand_fn", 10.0, 1, 10, 0.0),
        ]
        faults = self.detector.detect("pkg", reports)
        # bedrock_fn vs stable_fn: gap=25, not enough (threshold=40)
        # bedrock_fn vs quicksand_fn: gap=85, fault!
        # stable_fn vs quicksand_fn: gap=60, fault!
        assert len(faults) == 2

    def test_with_related_functions(self):
        reports = [
            BedrockReport("pkg", "fn1", 95.0, 9, 10, 3.0),
            BedrockReport("pkg", "fn2", 10.0, 1, 10, 0.0),
            BedrockReport("pkg", "fn3", 50.0, 5, 10, 0.5),
        ]
        # Only check fn1 vs fn2 (they're related)
        related = [("fn1", "fn2")]
        faults = self.detector.detect("pkg", reports, related_functions=related)
        assert len(faults) == 1
        assert faults[0].bedrock_function == "fn1"

    def test_detect_from_reports_groups_by_package(self):
        reports = [
            BedrockReport("pkg1", "fn1", 95.0, 9, 10, 3.0),
            BedrockReport("pkg1", "fn2", 10.0, 1, 10, 0.0),
            BedrockReport("pkg2", "fn3", 90.0, 9, 10, 2.0),
            BedrockReport("pkg2", "fn4", 30.0, 3, 10, 0.5),
        ]
        faults = self.detector.detect_from_reports(reports)
        # pkg1: fn1 vs fn2 gap=85, fault
        # pkg2: fn3 vs fn4 gap=60, fault
        assert len(faults) == 2

    def test_description_content(self):
        reports = [
            BedrockReport("pkg", "good_fn", 95.0, 9, 10, 3.0),
            BedrockReport("pkg", "bad_fn", 10.0, 1, 10, 0.0),
        ]
        faults = self.detector.detect("pkg", reports)
        assert "good_fn" in faults[0].description
        assert "bad_fn" in faults[0].description
        assert "95" in faults[0].description
        assert "10" in faults[0].description

    def test_empty_reports(self):
        faults = self.detector.detect("pkg", [])
        assert len(faults) == 0
