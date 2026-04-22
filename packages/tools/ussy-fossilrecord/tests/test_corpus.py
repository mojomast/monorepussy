"""Tests for the corpus loader module."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from fossilrecord.corpus.loader import (
    CorpusLoader,
    EsolangProgram,
    StressCategory,
    load_corpus,
)


class TestStressCategory:
    """Tests for StressCategory enum."""

    def test_all_categories_exist(self):
        expected = {
            "whitespace", "2d", "self-modifying", "visual",
            "natural-language", "parody", "concise", "obfuscated",
            "minimalistic", "embedded",
        }
        actual = {c.value for c in StressCategory}
        assert actual == expected

    def test_category_from_value(self):
        assert StressCategory("whitespace") == StressCategory.WHITESPACE
        assert StressCategory("2d") == StressCategory.TWOD
        assert StressCategory("self-modifying") == StressCategory.SELF_MODIFYING

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            StressCategory("nonexistent")


class TestEsolangProgram:
    """Tests for EsolangProgram dataclass."""

    def test_create_basic_program(self):
        prog = EsolangProgram(
            name="Test Program",
            language="Brainfuck",
            source="++.",
            expected_behavior="Outputs something",
            categories=[StressCategory.MINIMALISTIC],
            difficulty=1,
        )
        assert prog.name == "Test Program"
        assert prog.language == "Brainfuck"
        assert prog.source == "++."
        assert prog.difficulty == 1

    def test_to_dict_round_trip(self):
        prog = EsolangProgram(
            name="BF Hello",
            language="Brainfuck",
            source="+++.",
            expected_behavior="Prints char",
            categories=[StressCategory.MINIMALISTIC, StressCategory.CONCISE],
            difficulty=2,
        )
        d = prog.to_dict()
        restored = EsolangProgram.from_dict(d)
        assert restored.name == prog.name
        assert restored.language == prog.language
        assert restored.source == prog.source
        assert restored.categories == prog.categories
        assert restored.difficulty == prog.difficulty

    def test_from_dict_with_unknown_category_ignored(self):
        d = {
            "name": "Test",
            "language": "FooLang",
            "source": "bar",
            "expected_behavior": "does bar",
            "categories": ["concise", "nonexistent_category"],
            "difficulty": 3,
        }
        prog = EsolangProgram.from_dict(d)
        assert StressCategory.CONCISE in prog.categories
        assert len(prog.categories) == 1  # unknown category ignored

    def test_load_source_inline(self):
        prog = EsolangProgram(
            name="Inline",
            language="Test",
            source="inline source",
            expected_behavior="",
            categories=[],
            difficulty=1,
        )
        assert prog.load_source() == "inline source"

    def test_load_source_from_file(self, tmp_path):
        source_file = tmp_path / "test.bf"
        source_file.write_text("+++-.", encoding="utf-8")
        prog = EsolangProgram(
            name="File",
            language="Brainfuck",
            source="",
            expected_behavior="",
            categories=[],
            difficulty=1,
            source_file="test.bf",
        )
        assert prog.load_source(tmp_path) == "+++-."

    def test_load_source_file_not_found(self, tmp_path):
        prog = EsolangProgram(
            name="Missing",
            language="Test",
            source="fallback",
            expected_behavior="",
            categories=[],
            difficulty=1,
            source_file="nonexistent.bf",
        )
        # Falls back to inline source
        assert prog.load_source(tmp_path) == "fallback"


class TestCorpusLoader:
    """Tests for CorpusLoader."""

    def test_load_default_corpus(self):
        loader = CorpusLoader()
        programs = loader.load()
        assert len(programs) >= 15  # Spec requires 15-20+

    def test_load_returns_list_of_esolang_program(self):
        loader = CorpusLoader()
        programs = loader.load()
        for prog in programs:
            assert isinstance(prog, EsolangProgram)

    def test_by_language(self):
        loader = CorpusLoader()
        bf_programs = loader.by_language("Brainfuck")
        assert len(bf_programs) >= 2
        for p in bf_programs:
            assert p.language == "Brainfuck"

    def test_by_language_case_insensitive(self):
        loader = CorpusLoader()
        bf1 = loader.by_language("brainfuck")
        bf2 = loader.by_language("BRAINFUCK")
        bf3 = loader.by_language("Brainfuck")
        assert len(bf1) == len(bf2) == len(bf3)

    def test_by_category(self):
        loader = CorpusLoader()
        ws_programs = loader.by_category(StressCategory.WHITESPACE)
        assert len(ws_programs) >= 1
        for p in ws_programs:
            assert StressCategory.WHITESPACE in p.categories

    def test_by_difficulty(self):
        loader = CorpusLoader()
        easy = loader.by_difficulty(1, 2)
        for p in easy:
            assert 1 <= p.difficulty <= 2

    def test_languages_list(self):
        loader = CorpusLoader()
        langs = loader.languages()
        assert len(langs) >= 5
        assert "Brainfuck" in langs

    def test_categories_list(self):
        loader = CorpusLoader()
        cats = loader.categories()
        assert len(cats) >= 3

    def test_reload(self):
        loader = CorpusLoader()
        first = loader.load()
        second = loader.reload()
        assert len(first) == len(second)

    def test_load_empty_corpus(self, tmp_path):
        corpus_file = tmp_path / "corpus.json"
        corpus_file.write_text('{"programs": []}', encoding="utf-8")
        loader = CorpusLoader(tmp_path)
        programs = loader.load()
        assert programs == []

    def test_load_missing_corpus_file(self, tmp_path):
        loader = CorpusLoader(tmp_path)
        programs = loader.load()
        assert programs == []

    def test_load_convenience_function(self):
        programs = load_corpus()
        assert len(programs) >= 15


class TestCorpusContent:
    """Test that the corpus has the required content."""

    def test_has_brainfuck(self):
        loader = CorpusLoader()
        assert len(loader.by_language("Brainfuck")) >= 3

    def test_has_befunge(self):
        loader = CorpusLoader()
        assert len(loader.by_language("Befunge-93")) >= 2

    def test_has_whitespace(self):
        loader = CorpusLoader()
        assert len(loader.by_language("Whitespace")) >= 1

    def test_has_intercal(self):
        loader = CorpusLoader()
        assert len(loader.by_language("INTERCAL")) >= 1

    def test_total_programs_count(self):
        loader = CorpusLoader()
        programs = loader.programs()
        assert len(programs) >= 20

    def test_all_programs_have_source(self):
        loader = CorpusLoader()
        for prog in loader.programs():
            assert prog.source, f"Program '{prog.name}' has no source"

    def test_all_difficulties_in_range(self):
        loader = CorpusLoader()
        for prog in loader.programs():
            assert 1 <= prog.difficulty <= 5, f"Program '{prog.name}' has invalid difficulty {prog.difficulty}"

    def test_all_programs_have_categories(self):
        loader = CorpusLoader()
        for prog in loader.programs():
            assert len(prog.categories) >= 1, f"Program '{prog.name}' has no categories"
