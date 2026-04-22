"""Weeding and Deaccession — Collection maintenance."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ussy_curator.utils import (
    flesch_reading_ease,
    jaccard_similarity,
    extract_code_references,
    extract_executable_blocks,
    validate_block,
)


class WeedingEngine:
    """
    Implements MUSTIE weeding criteria for documentation.
    """

    CRITERIA = {
        "M": "Misleading",
        "U": "Ugly",
        "S": "Superseded",
        "T": "Trivial",
        "I": "Irrelevant",
        "E": "Erroneous",
    }

    def evaluate(self, doc: Any, collection: list[Any]) -> dict[str, float]:
        """
        Evaluates a document against MUSTIE criteria.
        Returns dict of triggered criteria with confidence scores.
        """
        results = {}
        results["M"] = self._check_misleading(doc)
        results["U"] = self._check_usability(doc)
        results["S"] = self._check_superseded(doc, collection)
        results["T"] = self._check_triviality(doc)
        results["I"] = self._check_relevance(doc)
        results["E"] = self._check_errors(doc)
        return results

    def _check_misleading(self, doc: Any) -> float:
        """
        Detects misleading content by comparing doc claims to code reality.
        """
        claims = self._extract_factual_claims(doc.content)
        if not claims:
            return 0.0
        verified = sum(1 for c in claims if self._verify_against_code(c, doc.referenced_code))
        return 1.0 - (verified / len(claims))

    def _extract_factual_claims(self, content: str) -> list[str]:
        """Extract simple factual claims from content."""
        # Heuristic: sentences with numbers or definite statements
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        claims = [s for s in sentences if any(ch.isdigit() for ch in s)]
        return claims if claims else sentences[:5]

    def _verify_against_code(self, claim: str, referenced_code: list[str]) -> bool:
        """Check if a claim is supported by referenced code."""
        # Simplified: if any reference matches keywords in the claim, consider verified
        claim_words = set(claim.lower().split())
        for ref in referenced_code:
            ref_words = set(ref.lower().split(".") if "." in ref else ref.lower().split())
            if claim_words & ref_words:
                return True
        return False

    def _check_usability(self, doc: Any) -> float:
        """
        Assesses document usability/readability.
        """
        ri = flesch_reading_ease(doc.content)
        return max(0.0, 1.0 - (ri / 100))

    def _check_superseded(self, doc: Any, collection: list[Any]) -> float:
        """
        Detects if document is superseded by another.
        """
        max_score = 0.0
        for other in collection:
            if other.path == doc.path:
                continue
            sim = jaccard_similarity(set(doc.keywords), set(other.keywords))
            ci_doc = doc.conservation_report.condition_index()
            ci_other = other.conservation_report.condition_index()
            freshness_ratio = ci_other / (ci_doc + 1e-6)
            score = sim * min(freshness_ratio, 2.0)
            max_score = max(max_score, score)
        return max_score

    def _check_triviality(self, doc: Any) -> float:
        """
        Measures content substance.
        """
        words = doc.word_count
        unique_concepts = len(doc.keywords)
        if words == 0:
            return 1.0
        density = unique_concepts / words
        return max(0.0, 1.0 - math.sqrt(density * 100))

    def _check_relevance(self, doc: Any) -> float:
        """
        Measures relevance to current project scope.
        """
        refs = extract_code_references(doc.content)
        if not refs:
            return 0.5
        current = sum(1 for r in refs if self._exists_in_current_codebase(r))
        return 1.0 - (current / len(refs))

    def _exists_in_current_codebase(self, ref: str) -> bool:
        """Check if a reference exists in the current codebase."""
        # Simplified heuristic: common standard library and built-in names exist
        stdlib = {"os", "sys", "json", "math", "re", "pathlib", "datetime", "typing"}
        return ref.split(".")[0] in stdlib

    def _check_errors(self, doc: Any) -> float:
        """
        Detects harmful errors (broken commands, incorrect APIs).
        """
        code_blocks = extract_executable_blocks(doc.content)
        if not code_blocks:
            return 0.0
        errors = sum(1 for block in code_blocks if not validate_block(block))
        return errors / len(code_blocks)

    def weed_score(self, evaluation: dict[str, float]) -> float:
        """
        Computes composite weeding score.
        """
        weights = {"E": 0.30, "M": 0.25, "S": 0.20, "I": 0.10, "U": 0.10, "T": 0.05}
        return sum(weights[c] * evaluation[c] for c in weights)

    def generate_deaccession_proposal(self, doc: Any, collection: list[Any]) -> dict[str, Any] | None:
        """Generates formal deaccession proposal with ethical safeguards."""
        eval_result = self.evaluate(doc, collection)
        score = self.weed_score(eval_result)

        if score < 0.5:
            return None

        triggered = [self.CRITERIA[k] for k, v in eval_result.items() if v > 0.5]

        return {
            "path": str(doc.path),
            "accession_number": doc.accession_number,
            "title": doc.title,
            "weed_score": round(score, 3),
            "triggered_criteria": triggered,
            "justification": (
                f"Document scores {score:.2f} on MUSTIE scale "
                f"primarily due to: {', '.join(triggered)}"
            ),
            "impact_assessment": {
                "incoming_links": len(doc.backlinks),
                "last_viewed": doc.last_accessed,
                "replacement_available": eval_result["S"] > 0.5,
            },
            "disposition": "archive" if doc.provenance_chain.get("completeness", 0) > 0.5 else "remove",
            "ethical_review": score > 0.8,
        }

    def batch_weed(self, collection: list[Any], threshold: float = 0.6) -> list[dict[str, Any]]:
        """Evaluates entire collection and returns deaccession candidates."""
        candidates = []
        for doc in collection:
            proposal = self.generate_deaccession_proposal(doc, collection)
            if proposal:
                candidates.append(proposal)
        return sorted(candidates, key=lambda x: x["weed_score"], reverse=True)
