"""Tests for curator.utils."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from curator import utils


class TestParseYamlFrontmatter:
    def test_extracts_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: Hello\nauthor: Ada\n---\n\nContent here.")
        fm = utils.parse_yaml_frontmatter(f)
        assert fm["title"] == "Hello"
        assert fm["author"] == "Ada"

    def test_empty_when_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Hello\n\nContent.")
        fm = utils.parse_yaml_frontmatter(f)
        assert fm == {}

    def test_list_tags(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text('---\ntags: [a, b, c]\n---\n')
        fm = utils.parse_yaml_frontmatter(f)
        assert isinstance(fm.get("tags"), list)


class TestInferTitle:
    def test_from_heading(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# My Title\n\nBody.")
        assert utils.infer_title(f) == "My Title"

    def test_from_filename(self, tmp_path: Path) -> None:
        f = tmp_path / "some_file-name.md"
        f.write_text("Body without heading.")
        assert utils.infer_title(f) == "Some File Name"


class TestInferAuthor:
    def test_from_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\nauthor: Grace\n---\n")
        assert utils.infer_author(f) == "Grace"

    def test_unknown_when_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("No frontmatter.")
        assert utils.infer_author(f) == "unknown"


class TestGitCreationDate:
    def test_returns_iso_string(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        result = utils.git_creation_date(f)
        assert result.startswith("20")
        assert "T" in result

    def test_missing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.md"
        result = utils.git_creation_date(f)
        assert result.startswith("20")


class TestClassifyDocType:
    def test_markdown(self) -> None:
        assert utils.classify_doc_type(Path("x.md")) == "markdown"

    def test_rst(self) -> None:
        assert utils.classify_doc_type(Path("x.rst")) == "restructuredtext"

    def test_unknown(self) -> None:
        assert utils.classify_doc_type(Path("x.xyz")) == "unknown"


class TestExtractMarkdownLinks:
    def test_extracts_local_links(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("See [other](other.md) and [http](http://example.com)")
        links = utils.extract_markdown_links(f)
        assert len(links) == 1
        assert links[0].text == "other"

    def test_no_links(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("No links here.")
        assert utils.extract_markdown_links(f) == []


class TestExtractKeywords:
    def test_returns_keywords(self) -> None:
        kw = utils.extract_keywords("python python code testing testing testing")
        assert "python" in kw
        assert "testing" in kw

    def test_ignores_stopwords(self) -> None:
        kw = utils.extract_keywords("the and with python")
        assert "the" not in kw
        assert "python" in kw


class TestFleschReadingEase:
    def test_simple_text_scores_high(self) -> None:
        score = utils.flesch_reading_ease("The cat sat. The dog ran.")
        assert score > 50

    def test_complex_text_scores_low(self) -> None:
        score = utils.flesch_reading_ease(
            "The amalgamation of disparate heterogeneous computational paradigms necessitates rigorous methodological scrutiny."
        )
        assert score < 50


class TestJaccardSimilarity:
    def test_identical_sets(self) -> None:
        assert utils.jaccard_similarity({1, 2, 3}, {1, 2, 3}) == 1.0

    def test_disjoint_sets(self) -> None:
        assert utils.jaccard_similarity({1, 2}, {3, 4}) == 0.0

    def test_partial_overlap(self) -> None:
        assert utils.jaccard_similarity({1, 2, 3}, {2, 3, 4}) == 0.5


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = {"a": 1.0, "b": 1.0}
        assert utils.cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = {"x": 1.0}
        b = {"y": 1.0}
        assert utils.cosine_similarity(a, b) == pytest.approx(0.0)


class TestVectorize:
    def test_basic(self) -> None:
        v = utils.vectorize("hello world hello")
        assert v["hello"] == pytest.approx(2 / 3)
        assert v["world"] == pytest.approx(1 / 3)


class TestExtractCodeReferences:
    def test_backtick_refs(self) -> None:
        refs = utils.extract_code_references("Use `os.path.join` and `json.dumps`.")
        assert any("os.path.join" in r for r in refs)


class TestExtractExecutableBlocks:
    def test_fenced_blocks(self) -> None:
        blocks = utils.extract_executable_blocks("```bash\necho hi\n```")
        assert len(blocks) == 1
        assert "echo hi" in blocks[0]


class TestValidateBlock:
    def test_valid_block(self) -> None:
        assert utils.validate_block("echo hello") is True

    def test_invalid_traceback(self) -> None:
        assert utils.validate_block("Traceback (most recent call):") is False


class TestSemverDistance:
    def test_same_version(self) -> None:
        assert utils.semver_distance("1.0.0", "1.0.0") == pytest.approx(0.0)

    def test_different_versions(self) -> None:
        assert utils.semver_distance("1.0.0", "2.0.0") > 0


class TestInferAudience:
    def test_expert(self) -> None:
        assert utils.infer_audience(20.0, 0.5) == "expert"

    def test_beginner(self) -> None:
        assert utils.infer_audience(80.0, 0.05) == "beginner"

    def test_general(self) -> None:
        assert utils.infer_audience(50.0, 0.15) == "general"


class TestAdaptSummary:
    def test_truncates_long_text(self) -> None:
        text = "word " * 100
        result = utils.adapt_summary(text, max_len=50)
        assert len(result) <= 55
        assert result.endswith("...")

    def test_simple_complexity(self) -> None:
        text = "Hello (details) world"
        result = utils.adapt_summary(text, max_len=200, complexity="simple")
        assert "(" not in result
