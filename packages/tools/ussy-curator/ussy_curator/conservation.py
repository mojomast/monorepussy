"""Conservation Report — Freshness and deterioration curves."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ussy_curator.utils import (
    git_last_edit,
    avg_age_of_referenced_code,
    extract_markdown_links,
    extract_dependencies,
    get_pinned_version,
    get_latest_version,
    semver_distance,
    edits_per_quarter,
)


class ConservationReport:
    """
    Generates a museum-style condition report for a document.
    """

    GRADES = ["Excellent", "Good", "Fair", "Poor", "Critical"]

    def __init__(self, doc_path: Path, codebase_state: dict[str, Any] | None = None) -> None:
        self.path = doc_path
        self.state = codebase_state or {}
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> dict[str, Any]:
        """Calculates deterioration metrics."""
        age_days = (datetime.now(timezone.utc) - git_last_edit(self.path)).days
        code_age = avg_age_of_referenced_code(self.path)
        dependency_drift = self._dependency_drift()
        link_rot = self._link_rot_ratio()

        return {
            "age_days": age_days,
            "code_age_delta": max(0, age_days - code_age),
            "dependency_drift": dependency_drift,
            "link_rot": link_rot,
            "edit_frequency": edits_per_quarter(self.path),
        }

    def deterioration_rate(self) -> float:
        """
        Computes documentation deterioration rate using modified Arrhenius model.
        """
        k_base = 1.0 / 365.0
        delta_code = self.metrics["code_age_delta"] / 365.0
        D_dep = self.metrics["dependency_drift"]
        L_rot = self.metrics["link_rot"]

        gamma, delta, epsilon = 0.5, 2.0, 1.5

        return k_base * math.exp(gamma * delta_code + delta * D_dep + epsilon * L_rot)

    def condition_index(self) -> float:
        """
        Computes overall condition on a 0-100 scale.
        """
        t = self.metrics["age_days"] / 365.0
        k = self.deterioration_rate()
        return 100 * math.exp(-k * t)

    def grade(self) -> str:
        """Maps condition index to conservation grade."""
        ci = self.condition_index()
        thresholds = [90, 70, 50, 30, 0]
        for i, thresh in enumerate(thresholds):
            if ci >= thresh:
                return self.GRADES[i]
        return self.GRADES[-1]

    def recommended_treatment(self) -> str:
        """Suggests conservation treatment based on condition."""
        ci = self.condition_index()
        if ci >= 90:
            return "Preventive conservation: schedule routine review"
        elif ci >= 70:
            return "Minor treatment: update examples, verify links"
        elif ci >= 50:
            return "Interventive treatment: rewrite outdated sections"
        elif ci >= 30:
            return "Major restoration: full rewrite against current code"
        else:
            return "Deaccession candidate: consider removal or archival"

    def _dependency_drift(self) -> float:
        """Measures how far referenced dependencies have drifted."""
        deps = extract_dependencies(self.path.read_text(encoding="utf-8") if self.path.exists() else "")
        if not deps:
            return 0.0
        drift_scores = []
        for dep in deps:
            pinned = get_pinned_version(self.path, dep)
            current = get_latest_version(dep)
            if pinned and current:
                drift_scores.append(semver_distance(pinned, current))
        return sum(drift_scores) / len(drift_scores) if drift_scores else 0.0

    def _link_rot_ratio(self) -> float:
        """Ratio of broken internal links."""
        links = extract_markdown_links(self.path)
        if not links:
            return 0.0
        broken = sum(1 for link in links if not link.target.exists())
        return broken / len(links)
