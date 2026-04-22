"""Evidence Collector.

Collects and correlates evidence from various sources:
- Git history analysis
- Incident database correlation
- Engineering blog post mining
- Community outcome database
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class EvidenceItem:
    """A single piece of evidence."""
    source: str  # git, incident, blog, community
    adr_id: str
    description: str
    timestamp: str = ""
    relevance: float = 1.0  # 0-1, how relevant this evidence is
    url: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self.relevance = max(0.0, min(1.0, self.relevance))


@dataclass
class IncidentRecord:
    """Record of a production incident."""
    incident_id: str
    title: str
    severity: str = "medium"  # low, medium, high, critical
    affected_adrs: List[str] = field(default_factory=list)
    timestamp: str = ""
    description: str = ""
    resolution: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class EvidenceCollector:
    """Collects evidence from multiple sources to support risk analysis."""

    def __init__(self):
        self.evidence: List[EvidenceItem] = []
        self.incidents: List[IncidentRecord] = []
        self.blog_entries: List[Dict] = []

    def add_evidence(self, item: EvidenceItem):
        """Add an evidence item."""
        self.evidence.append(item)

    def add_incident(self, incident: IncidentRecord):
        """Add an incident record."""
        self.incidents.append(incident)
        # Auto-create evidence for each affected ADR
        for adr_id in incident.affected_adrs:
            self.add_evidence(EvidenceItem(
                source="incident",
                adr_id=adr_id,
                description=f"Incident {incident.incident_id}: {incident.title}",
                timestamp=incident.timestamp,
                relevance={"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}.get(
                    incident.severity, 0.5
                ),
            ))

    def load_incidents_from_json(self, filepath: str):
        """Load incident records from a JSON file."""
        import json

        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            self.add_incident(IncidentRecord(
                incident_id=item.get("incident_id", ""),
                title=item.get("title", ""),
                severity=item.get("severity", "medium"),
                affected_adrs=item.get("affected_adrs", []),
                timestamp=item.get("timestamp", ""),
                description=item.get("description", ""),
                resolution=item.get("resolution", ""),
            ))

    def analyze_git_history(self, repo_path: str, adr_id: str) -> List[EvidenceItem]:
        """Analyze git history for evidence related to a decision.

        This is a simplified analysis that looks at commit messages.
        In production, this would use git log with proper parsing.
        """
        items = []
        # Look for a git log file as a proxy
        log_file = os.path.join(repo_path, "git_log.txt")
        if not os.path.exists(log_file):
            return items

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Simple pattern: look for ADR references in commit messages
                if adr_id.lower() in line.lower():
                    items.append(EvidenceItem(
                        source="git",
                        adr_id=adr_id,
                        description=f"Git commit references {adr_id}: {line[:100]}",
                        relevance=0.6,
                    ))

        self.evidence.extend(items)
        return items

    def load_blog_entries(self, filepath: str):
        """Load engineering blog post entries from a JSON file."""
        import json

        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            self.blog_entries.append(entry)
            # Extract ADR references from content
            content = entry.get("content", "")
            title = entry.get("title", "")
            # Find ADR references
            adr_refs = re.findall(r'ADR-?\d+', content, re.IGNORECASE)
            for ref in set(adr_refs):
                self.add_evidence(EvidenceItem(
                    source="blog",
                    adr_id=ref.upper(),
                    description=f"Blog post '{title}' discusses {ref}",
                    url=entry.get("url", ""),
                    relevance=0.4,
                ))

    def get_evidence_for_card(self, adr_id: str) -> List[EvidenceItem]:
        """Get all evidence items for a specific card."""
        return [
            e for e in self.evidence
            if e.adr_id.upper() == adr_id.upper()
        ]

    def get_incidents_for_card(self, adr_id: str) -> List[IncidentRecord]:
        """Get all incidents that affected a specific card."""
        return [
            i for i in self.incidents
            if adr_id.upper() in [a.upper() for a in i.affected_adrs]
        ]

    def compute_incident_correlation(self, adr_id: str) -> float:
        """Compute correlation between a decision and incidents.

        Returns a value between 0 and 1 indicating how strongly
        this decision correlates with incidents.
        """
        incidents = self.get_incidents_for_card(adr_id)
        if not incidents:
            return 0.0

        # Weight by severity
        severity_weights = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
        }

        total_weight = sum(
            severity_weights.get(i.severity, 0.5) for i in incidents
        )
        # Normalize: 1 critical incident = 0.3 correlation, scales up
        correlation = min(1.0, total_weight * 0.15)
        return round(correlation, 3)

    def evidence_summary(self, adr_id: str) -> Dict:
        """Generate a summary of evidence for a card."""
        evidence_items = self.get_evidence_for_card(adr_id)
        incidents = self.get_incidents_for_card(adr_id)

        by_source: Dict[str, int] = {}
        for item in evidence_items:
            by_source[item.source] = by_source.get(item.source, 0) + 1

        avg_relevance = 0.0
        if evidence_items:
            avg_relevance = sum(e.relevance for e in evidence_items) / len(evidence_items)

        return {
            "adr_id": adr_id,
            "evidence_count": len(evidence_items),
            "incident_count": len(incidents),
            "incident_correlation": self.compute_incident_correlation(adr_id),
            "sources": by_source,
            "average_relevance": round(avg_relevance, 2),
        }
