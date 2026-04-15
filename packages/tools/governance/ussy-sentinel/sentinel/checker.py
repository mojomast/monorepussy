"""Anomaly scoring and checking.

Compares code patterns against a detector population and produces
anomaly scores with explanations.
"""

import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .detectors import Detector, DetectorPopulation
from .distance import euclidean_distance
from .extractor import FeatureVector, extract_patterns_from_directory, extract_patterns_from_file


@dataclass
class Detection:
    """A single detector firing on a pattern."""
    detector_id: str
    pattern_name: str
    pattern_kind: str
    source_file: str
    source_line: int
    distance: float
    threshold: float
    detector_vector: List[float] = field(default_factory=list)
    pattern_vector: List[float] = field(default_factory=list)

    @property
    def strength(self) -> float:
        """How strongly this detector fired (1.0 = exact match, 0.0 = at threshold)."""
        if self.threshold <= 0:
            return 1.0
        return max(0.0, 1.0 - (self.distance / self.threshold))


@dataclass
class AnomalyReport:
    """Anomaly report for a file or directory."""
    target: str
    anomaly_score: float = 0.0
    detections: List[Detection] = field(default_factory=list)
    num_patterns_checked: int = 0
    num_detectors_fired: int = 0
    self_context: Dict = field(default_factory=dict)

    @property
    def severity(self) -> str:
        """Classify anomaly severity."""
        if self.anomaly_score < 0.2:
            return "NORMAL"
        elif self.anomaly_score < 0.4:
            return "LOW"
        elif self.anomaly_score < 0.6:
            return "MODERATE"
        elif self.anomaly_score < 0.8:
            return "ELEVATED"
        else:
            return "CRITICAL"

    @property
    def is_anomalous(self) -> bool:
        """Whether the anomaly score exceeds the default threshold."""
        return self.anomaly_score >= 0.5


def check_patterns(
    patterns: List[FeatureVector],
    population: DetectorPopulation,
    threshold: float = 0.5,
    metric: str = "euclidean",
) -> AnomalyReport:
    """Check a list of patterns against a detector population.

    Args:
        patterns: List of feature vectors to check
        population: Detector population
        threshold: Anomaly score threshold for flagging
        metric: Distance metric

    Returns:
        AnomalyReport with detections and scoring
    """
    if not patterns:
        return AnomalyReport(target="", anomaly_score=0.0)

    target = patterns[0].source_file or "<unknown>"
    detections = []

    for pattern in patterns:
        pattern_vec = pattern.to_list()
        for detector in population.detectors:
            if detector.matches(pattern_vec, metric):
                dist = detector.distance_to(pattern_vec, metric)
                detection = Detection(
                    detector_id=detector.id,
                    pattern_name=pattern.name,
                    pattern_kind=pattern.kind,
                    source_file=pattern.source_file,
                    source_line=pattern.source_line,
                    distance=dist,
                    threshold=detector.threshold,
                    detector_vector=detector.vector,
                    pattern_vector=pattern_vec,
                )
                detections.append(detection)

    # Compute anomaly score
    # Based on: fraction of patterns with at least one detection,
    # weighted by detection strength
    if not patterns:
        anomaly_score = 0.0
    else:
        patterns_with_detections = set()
        total_strength = 0.0
        for det in detections:
            patterns_with_detections.add((det.pattern_name, det.source_file, det.source_line))
            total_strength += det.strength

        # Score = weighted combination of coverage and strength
        coverage_ratio = len(patterns_with_detections) / len(patterns)
        avg_strength = total_strength / max(len(detections), 1)
        anomaly_score = coverage_ratio * 0.6 + avg_strength * 0.4
        anomaly_score = min(1.0, anomaly_score)

    report = AnomalyReport(
        target=target,
        anomaly_score=round(anomaly_score, 3),
        detections=detections,
        num_patterns_checked=len(patterns),
        num_detectors_fired=len(detections),
    )

    return report


def check_file(
    filepath: str,
    population: DetectorPopulation,
    granularity: str = "function",
    threshold: float = 0.5,
    metric: str = "euclidean",
) -> AnomalyReport:
    """Check a single file for anomalies."""
    patterns = extract_patterns_from_file(filepath, granularity)
    report = check_patterns(patterns, population, threshold, metric)
    report.target = filepath
    return report


def check_directory(
    dirpath: str,
    population: DetectorPopulation,
    granularity: str = "function",
    threshold: float = 0.5,
    metric: str = "euclidean",
) -> List[AnomalyReport]:
    """Check all Python files in a directory for anomalies."""
    reports = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', '.git', 'venv', '.venv')]
        for fname in sorted(files):
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                report = check_file(fpath, population, granularity, threshold, metric)
                reports.append(report)
    return reports


def explain_detection(detection: Detection, feature_names: List[str]) -> str:
    """Generate a human-readable explanation of why a detector fired.

    Identifies which feature dimensions differ most between the detector
    and the matched pattern.
    """
    diffs = [(abs(d - p), i) for i, (d, p) in enumerate(
        zip(detection.detector_vector, detection.pattern_vector))]
    diffs.sort(reverse=True)

    top_features = []
    for diff, idx in diffs[:3]:
        if idx < len(feature_names):
            top_features.append(f"{feature_names[idx]} (Δ={diff:.3f})")

    explanation = (
        f"  [{detection.detector_id}] Pattern '{detection.pattern_name}' "
        f"({detection.pattern_kind}) at {detection.source_file}:{detection.source_line}\n"
        f"    → Distance: {detection.distance:.3f} (threshold: {detection.threshold:.3f})\n"
        f"    → Strength: {detection.strength:.2f}\n"
        f"    → Top differing features: {', '.join(top_features)}"
    )
    return explanation


def format_report(report: AnomalyReport, explain: bool = False) -> str:
    """Format an anomaly report for display.

    Args:
        report: The anomaly report
        explain: Whether to include detailed explanations

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("")
    lines.append("🛡️  SENTINEL REPORT: " + os.path.basename(report.target))
    lines.append("━" * 50)

    severity = report.severity
    score_str = f"{report.anomaly_score:.2f}"
    lines.append(f"ANOMALY SCORE: {score_str} / 1.0 ({severity})")
    lines.append("")

    if report.detections:
        lines.append(f"Detectors Fired: {report.num_detectors_fired}")
        feature_names = FeatureVector.feature_names()

        # Group by pattern
        seen_patterns = set()
        for det in report.detections:
            key = (det.pattern_name, det.source_file, det.source_line)
            if key in seen_patterns:
                continue
            seen_patterns.add(key)
            if explain:
                lines.append(explain_detection(det, feature_names))
            else:
                lines.append(
                    f"  [{det.detector_id}] {det.pattern_name} "
                    f"at line {det.source_line} "
                    f"(dist={det.distance:.3f}, strength={det.strength:.2f})"
                )
        lines.append("")
    else:
        lines.append("No detectors fired — code appears consistent with self-profile.")
        lines.append("")

    # Context
    lines.append(f"Patterns checked: {report.num_patterns_checked}")
    if report.self_context:
        lines.append(f"Self-Normal Context:")
        for k, v in report.self_context.items():
            lines.append(f"  {k}: {v}")

    return '\n'.join(lines)
