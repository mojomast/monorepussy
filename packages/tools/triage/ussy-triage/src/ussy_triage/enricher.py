"""Context Enricher — Gathers surrounding context for diagnosed errors.

Enriches errors with:
- Git blame and recent commit history
- Project history of similar errors
- File-level context
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

from .models import EnrichedError, GitContext, HistoryMatch, VictimType
from .extractor import IsolatedError, ErrorExtractor
from .patterns import PatternMatcher


class ContextEnricher:
    """Enriches extracted errors with git context and pattern matches."""

    def __init__(self, project_dir: str = None, pattern_matcher: PatternMatcher = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.pattern_matcher = pattern_matcher or PatternMatcher()
        self._git_available = None

    @property
    def git_available(self) -> bool:
        """Check if git is available and we're in a git repo."""
        if self._git_available is None:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=str(self.project_dir),
                    capture_output=True, text=True, timeout=5
                )
                self._git_available = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._git_available = False
        return self._git_available

    def enrich(self, error: IsolatedError) -> EnrichedError:
        """Enrich a single extracted error with patterns and context."""
        # Match against pattern database
        matched_pattern = self.pattern_matcher.match(
            error.content,
            error_type=error.error_type,
            language=error.language,
        )

        # Classify victim type
        victim_type = self.pattern_matcher.classify_victim(error.error_type)

        # Get git context
        git_context = None
        if self.git_available and error.file_path:
            git_context = self._get_git_context(error.file_path, error.line_in_file)

        # Search project history for similar errors
        history_matches = []
        if self.git_available:
            history_matches = self._search_history(error.content)

        return EnrichedError(
            line_number=error.line_number,
            content=error.content,
            context_before=error.context_before,
            context_after=error.context_after,
            error_type=error.error_type,
            language=error.language,
            file_path=error.file_path,
            line_in_file=error.line_in_file,
            severity=error.severity,
            victim_type=victim_type,
            matched_pattern=matched_pattern,
            git_context=git_context,
            history_matches=history_matches,
        )

    def enrich_all(self, errors: List[IsolatedError]) -> List[EnrichedError]:
        """Enrich a list of extracted errors."""
        return [self.enrich(error) for error in errors]

    def _get_git_context(self, file_path: str,
                         line_number: Optional[int] = None) -> Optional[GitContext]:
        """Get git blame and recent commits for a file."""
        context = GitContext()

        try:
            # Get blame info
            if line_number:
                blame_result = subprocess.run(
                    ["git", "blame", "-L", f"{line_number},{line_number}",
                     "--porcelain", file_path],
                    cwd=str(self.project_dir),
                    capture_output=True, text=True, timeout=10
                )
                if blame_result.returncode == 0:
                    for line in blame_result.stdout.splitlines():
                        if line.startswith("author "):
                            context.author = line[7:]
                        elif line.startswith("summary "):
                            context.commit_message = line[8:]
                        elif line.startswith("commit-hash"):
                            context.commit_hash = line.split()[1] if len(line.split()) > 1 else None

            # Get recent commits to the file
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-5", file_path],
                cwd=str(self.project_dir),
                capture_output=True, text=True, timeout=10
            )
            if log_result.returncode == 0:
                for line in log_result.stdout.strip().splitlines():
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        context.recent_commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return context if (context.author or context.recent_commits) else None

    def _search_history(self, error_content: str) -> List[HistoryMatch]:
        """Search git history for similar error patterns."""
        matches = []

        # Extract key terms from the error
        terms = self._extract_search_terms(error_content)
        if not terms:
            return matches

        # Search in git log for commits mentioning these terms
        for term in terms[:3]:  # Limit to top 3 terms
            try:
                result = subprocess.run(
                    ["git", "log", "--all", "--oneline", "-10", "--grep", term],
                    cwd=str(self.project_dir),
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().splitlines():
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            commit_hash = parts[0]
                            commit_msg = parts[1]
                            # Simple similarity based on term overlap
                            similarity = sum(
                                1 for t in terms if t.lower() in commit_msg.lower()
                            ) / len(terms)
                            matches.append(HistoryMatch(
                                commit_hash=commit_hash,
                                commit_message=commit_msg,
                                similarity=round(similarity, 2),
                            ))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # Deduplicate by commit hash
        seen = set()
        unique_matches = []
        for m in sorted(matches, key=lambda x: x.similarity, reverse=True):
            if m.commit_hash not in seen:
                seen.add(m.commit_hash)
                unique_matches.append(m)

        return unique_matches[:5]  # Top 5 matches

    def _extract_search_terms(self, error_content: str) -> List[str]:
        """Extract meaningful search terms from error content."""
        # Remove common noise words
        noise_words = {
            "error", "the", "a", "an", "is", "not", "for", "to", "of",
            "in", "or", "and", "but", "was", "has", "had", "be", "been",
            "from", "by", "with", "that", "this", "it", "at", "on",
        }

        # Split into words, filter
        words = re.findall(r'\b\w{3,}\b', error_content.lower())
        terms = [w for w in words if w not in noise_words]

        return terms[:10]  # Top 10 terms
