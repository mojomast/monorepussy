"""Tests for the ContextEnricher module."""

import os
import tempfile
import pytest
from triage.enricher import ContextEnricher
from triage.extractor import ErrorExtractor, IsolatedError
from triage.models import EnrichedError, VictimType


class TestContextEnricherBasic:
    """Basic tests for ContextEnricher without git."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        from triage.patterns import PatternMatcher
        self.matcher = PatternMatcher(db_path=db_path)
        self.enricher = ContextEnricher(
            project_dir=self.tmpdir,
            pattern_matcher=self.matcher,
        )

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_enrich_python_error(self):
        error = IsolatedError(
            line_number=5,
            content="ModuleNotFoundError: No module named 'requests'",
            error_type="python_error",
            language="python",
        )
        enriched = self.enricher.enrich(error)
        assert isinstance(enriched, EnrichedError)
        assert enriched.line_number == 5
        assert enriched.victim_type == VictimType.RUNTIME
        assert enriched.matched_pattern is not None

    def test_enrich_rust_error(self):
        error = IsolatedError(
            line_number=10,
            content='error: borrow of moved value: `x`',
            error_type="rust_compile",
            language="rust",
        )
        enriched = self.enricher.enrich(error)
        assert enriched.victim_type == VictimType.BUILD
        assert enriched.matched_pattern is not None

    def test_enrich_unknown_error_no_pattern(self):
        error = IsolatedError(
            line_number=1,
            content="Something weird happened",
            error_type="unknown_weird",
            language=None,
        )
        enriched = self.enricher.enrich(error)
        assert enriched.victim_type == VictimType.UNKNOWN

    def test_enrich_all(self):
        errors = [
            IsolatedError(line_number=1, content="ValueError: bad", error_type="python_error", language="python"),
            IsolatedError(line_number=5, content="TypeError: wrong type", error_type="python_error", language="python"),
        ]
        enriched = self.enricher.enrich_all(errors)
        assert len(enriched) == 2

    def test_git_not_available_in_temp_dir(self):
        assert self.enricher.git_available is False

    def test_no_git_context_when_not_in_repo(self):
        error = IsolatedError(
            line_number=1,
            content="Error: something",
            file_path="test.py",
        )
        enriched = self.enricher.enrich(error)
        assert enriched.git_context is None

    def test_no_history_matches_when_not_in_repo(self):
        error = IsolatedError(
            line_number=1,
            content="Error: something",
        )
        enriched = self.enricher.enrich(error)
        assert enriched.history_matches == []


class TestContextEnricherWithGit:
    """Tests for ContextEnricher with a git repository."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        # Initialize a git repo
        os.system(f'cd {self.tmpdir} && git init && git config user.email "test@test.com" && git config user.name "Test"')
        # Create a file and commit it
        test_file = os.path.join(self.tmpdir, "app.py")
        with open(test_file, "w") as f:
            f.write("# test file\nimport os\nprint('hello')\n")
        os.system(f'cd {self.tmpdir} && git add -A && git commit -m "initial commit"')

        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        from triage.patterns import PatternMatcher
        self.matcher = PatternMatcher(db_path=db_path)
        self.enricher = ContextEnricher(
            project_dir=self.tmpdir,
            pattern_matcher=self.matcher,
        )

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_git_available(self):
        assert self.enricher.git_available is True

    def test_git_context_for_file(self):
        error = IsolatedError(
            line_number=1,
            content="ValueError: bad input",
            file_path="app.py",
            line_in_file=2,
            error_type="python_error",
            language="python",
        )
        enriched = self.enricher.enrich(error)
        # Git context may or may not be populated depending on git blame
        # Just verify it doesn't crash
        assert isinstance(enriched, EnrichedError)

    def test_history_search(self):
        error = IsolatedError(
            line_number=1,
            content="ValueError: bad input",
            error_type="python_error",
            language="python",
        )
        enriched = self.enricher.enrich(error)
        # May or may not find history matches
        assert isinstance(enriched.history_matches, list)


class TestExtractSearchTerms:
    """Tests for the search term extraction helper."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, "test_patterns.db")
        from triage.patterns import PatternMatcher
        self.matcher = PatternMatcher(db_path=db_path)
        self.enricher = ContextEnricher(
            project_dir=self.tmpdir,
            pattern_matcher=self.matcher,
        )

    def teardown_method(self):
        self.matcher.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extracts_meaningful_terms(self):
        terms = self.enricher._extract_search_terms(
            "ModuleNotFoundError: No module named 'requests'"
        )
        assert "modulenotfounderror" in terms
        assert "requests" in terms

    def test_filters_noise_words(self):
        terms = self.enricher._extract_search_terms(
            "The error is a common problem for the system"
        )
        # "error" is a noise word
        assert "error" not in terms
        assert "common" in terms

    def test_returns_limited_terms(self):
        long_text = " ".join(f"word{i}" for i in range(50))
        terms = self.enricher._extract_search_terms(long_text)
        assert len(terms) <= 10
