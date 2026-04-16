"""Corpus loader: loads esolang programs from JSON data files."""
from __future__ import annotations

import json
import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class StressCategory(enum.Enum):
    """What dimension of tool robustness an esolang stress-tests."""
    WHITESPACE = "whitespace"          # Invisible code / non-standard char sets
    TWOD = "2d"                        # 2D code / non-linear control flow
    SELF_MODIFYING = "self-modifying"  # Self-modifying code / encrypted semantics
    VISUAL = "visual"                  # Image-based code / visual programming
    NATURAL_LANGUAGE = "natural-language"  # Natural language syntax / extreme verbosity
    PARODY = "parody"                  # Parody constructs / intentional absurdity
    CONCISE = "concise"                # Extreme conciseness / symbol overload
    OBFUSCATED = "obfuscated"          # Intentional obfuscation
    MINIMALISTIC = "minimalistic"      # Extremely few instructions
    EMBEDDED = "embedded"              # Code meant to be embedded in other contexts


@dataclass
class EsolangProgram:
    """A single esolang program entry in the corpus."""
    name: str
    language: str
    source: str
    expected_behavior: str
    categories: list[StressCategory]
    difficulty: int  # 1-5
    source_file: str | None = None  # relative path to source file in corpus data

    def load_source(self, corpus_dir: Path | None = None) -> str:
        """Load the source code, either from the inline string or from a file."""
        if self.source:
            return self.source
        if self.source_file and corpus_dir:
            filepath = corpus_dir / self.source_file
            if filepath.exists():
                return filepath.read_text(encoding="utf-8", errors="replace")
        return self.source

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "language": self.language,
            "source": self.source,
            "expected_behavior": self.expected_behavior,
            "categories": [c.value for c in self.categories],
            "difficulty": self.difficulty,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EsolangProgram:
        categories = []
        for c in data.get("categories", []):
            try:
                categories.append(StressCategory(c))
            except ValueError:
                pass
        return cls(
            name=data["name"],
            language=data["language"],
            source=data.get("source", ""),
            expected_behavior=data.get("expected_behavior", ""),
            categories=categories,
            difficulty=data.get("difficulty", 1),
            source_file=data.get("source_file"),
        )


class CorpusLoader:
    """Loads and manages the esolang corpus."""

    def __init__(self, corpus_dir: Path | None = None):
        if corpus_dir is None:
            corpus_dir = Path(__file__).parent / "data"
        self.corpus_dir = Path(corpus_dir)
        self._programs: list[EsolangProgram] | None = None

    def load(self) -> list[EsolangProgram]:
        """Load all programs from the corpus JSON file."""
        if self._programs is not None:
            return self._programs

        corpus_file = self.corpus_dir / "corpus.json"
        if not corpus_file.exists():
            self._programs = []
            return self._programs

        with open(corpus_file, "r", encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw, strict=False)

        self._programs = [
            EsolangProgram.from_dict(entry) for entry in data.get("programs", [])
        ]
        return self._programs

    def programs(self) -> list[EsolangProgram]:
        """Get all programs, loading if necessary."""
        if self._programs is None:
            self.load()
        return self._programs  # type: ignore[return-value]

    def by_language(self, language: str) -> list[EsolangProgram]:
        """Filter programs by esolang name."""
        return [p for p in self.programs() if p.language.lower() == language.lower()]

    def by_category(self, category: StressCategory) -> list[EsolangProgram]:
        """Filter programs by stress category."""
        return [p for p in self.programs() if category in p.categories]

    def by_difficulty(self, min_diff: int = 1, max_diff: int = 5) -> list[EsolangProgram]:
        """Filter programs by difficulty range."""
        return [p for p in self.programs() if min_diff <= p.difficulty <= max_diff]

    def languages(self) -> list[str]:
        """Get unique language names in the corpus."""
        seen = set()
        result = []
        for p in self.programs():
            if p.language not in seen:
                seen.add(p.language)
                result.append(p.language)
        return result

    def categories(self) -> list[StressCategory]:
        """Get unique stress categories in the corpus."""
        seen = set()
        result = []
        for p in self.programs():
            for c in p.categories:
                if c not in seen:
                    seen.add(c)
                    result.append(c)
        return result

    def reload(self) -> list[EsolangProgram]:
        """Force reload from disk."""
        self._programs = None
        return self.load()


def load_corpus(corpus_dir: Path | None = None) -> list[EsolangProgram]:
    """Convenience function to load the corpus."""
    loader = CorpusLoader(corpus_dir)
    return loader.load()
