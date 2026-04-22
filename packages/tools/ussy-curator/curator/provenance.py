"""Provenance Tracker — Accession numbers and authorship lineage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from curator.storage import Storage


@dataclass
class MockCommit:
    """Represents a simplified commit for provenance tracking."""
    hash: str
    date: datetime
    author: str
    file_path: Path
    lines_changed: int
    lines_without_author_signature: int
    parents: int = 1

    __test__ = False


class ProvenanceTracker:
    """
    Maintains accession numbers and provenance chains for documents.
    """

    def __init__(self, registry_db: Storage) -> None:
        self.db = registry_db

    def accession(self, doc_path: Path, submitter: str = "system", origin: str = "internal") -> str:
        """
        Accession a new document into the collection.
        Returns unique accession number: YYYY.NNN.FFF
        """
        year = datetime.now(timezone.utc).year
        seq = self.db.next_acquisition_sequence(year)
        file_seq = 1
        accession_number = f"{year}.{seq:03d}.{file_seq:03d}"

        self.db.record_accession({
            "accession_number": accession_number,
            "path": str(doc_path),
            "submitter": submitter,
            "date": datetime.now(timezone.utc).isoformat(),
            "origin": origin,
            "status": "accessioned",
        })

        return accession_number

    def build_provenance_chain(self, doc_path: Path) -> dict[str, Any]:
        """
        Reconstructs provenance chain from file history.
        Each link in the chain represents a custodial event.
        """
        commits = self._get_file_commits(doc_path)
        chain = []

        for i, commit in enumerate(commits):
            prev = commits[i - 1] if i > 0 else None
            event_type = self._classify_event(commit, prev)
            chain.append({
                "event_id": commit.hash[:8],
                "date": commit.date.isoformat(),
                "custodian": commit.author,
                "event_type": event_type,
                "extent": commit.lines_changed,
                "confidence": self._attribution_confidence(commit),
            })

        return {
            "accession_number": self.db.get_accession(doc_path) or "",
            "chain": chain,
            "completeness": self._chain_completeness(chain),
            "gaps": self._find_gaps(chain),
        }

    def _get_file_commits(self, doc_path: Path) -> list[MockCommit]:
        """Generate synthetic commits from file metadata."""
        if not doc_path.exists():
            return []
        stat = doc_path.stat()
        creation = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
        modification = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        commits: list[MockCommit] = []
        # Creation commit
        commits.append(MockCommit(
            hash="a" * 40,
            date=creation,
            author="original_author",
            file_path=doc_path,
            lines_changed=max(1, stat.st_size // 50),
            lines_without_author_signature=0,
            parents=0,
        ))
        # If modified after creation, add a revision
        if modification > creation:
            commits.append(MockCommit(
                hash="b" * 40,
                date=modification,
                author="subsequent_editor",
                file_path=doc_path,
                lines_changed=max(1, stat.st_size // 100),
                lines_without_author_signature=2,
                parents=1,
            ))
        return commits

    def _classify_event(self, commit: MockCommit, previous: MockCommit | None) -> str:
        """Classifies the type of custodial event."""
        if previous is None:
            return "creation"
        if commit.parents > 1:
            return "merge"
        if commit.file_path != previous.file_path:
            return "move"
        if commit.lines_changed > previous.lines_changed * 0.8:
            return "restoration"
        return "revision"

    def _attribution_confidence(self, commit: MockCommit) -> float:
        """
        Scores confidence in authorship attribution.
        """
        total = commit.lines_changed
        unsigned = commit.lines_without_author_signature
        return max(0.0, 1.0 - (unsigned / total)) if total > 0 else 0.0

    def _chain_completeness(self, chain: list[dict[str, Any]]) -> float:
        """
        Measures provenance chain completeness.
        """
        if not chain:
            return 0.0
        start = datetime.fromisoformat(chain[0]["date"])
        end = datetime.fromisoformat(chain[-1]["date"])
        age_days = (end - start).days
        expected = max(1, age_days / 30)
        return min(1.0, len(chain) / expected)

    def _find_gaps(self, chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identifies temporal gaps in provenance."""
        gaps = []
        for i in range(1, len(chain)):
            prev_date = datetime.fromisoformat(chain[i - 1]["date"])
            curr_date = datetime.fromisoformat(chain[i]["date"])
            delta = (curr_date - prev_date).days
            if delta > 180:
                gaps.append({
                    "start": chain[i - 1]["date"],
                    "end": chain[i]["date"],
                    "duration_days": delta,
                    "severity": "major" if delta > 365 else "minor",
                })
        return gaps

    def line_of_custody_valid(self, doc_path: Path) -> bool:
        """Checks if line of custody is unbroken and attributable."""
        chain_data = self.build_provenance_chain(doc_path)
        return (
            chain_data["completeness"] > 0.5 and
            len(chain_data["gaps"]) == 0 and
            all(link["confidence"] > 0.7 for link in chain_data["chain"])
        )
