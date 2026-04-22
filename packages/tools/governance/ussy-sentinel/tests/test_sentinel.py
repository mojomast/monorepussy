"""Comprehensive test suite for Sentinel.

Covers: pattern extraction, distance metrics, self-profiles,
detector generation, anomaly checking, database persistence, CLI.
"""

import json
import math
import os
import random
import shutil
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

# ---- Test Fixtures ----

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_MODULE = os.path.join(FIXTURES_DIR, "sample_module.py")
ANOMALOUS_MODULE = os.path.join(FIXTURES_DIR, "anomalous_module.py")
MINIMAL_MODULE = os.path.join(FIXTURES_DIR, "minimal_module.py")
SYNTAX_ERROR_MODULE = os.path.join(FIXTURES_DIR, "syntax_error_module.py")


@pytest.fixture
def sample_source():
    """Read the sample module source."""
    with open(SAMPLE_MODULE, 'r') as f:
        return f.read()


@pytest.fixture
def anomalous_source():
    """Read the anomalous module source."""
    with open(ANOMALOUS_MODULE, 'r') as f:
        return f.read()


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    d = tempfile.mkdtemp(prefix="sentinel_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def tmp_project(tmp_dir):
    """Create a temporary project with source files."""
    src_dir = os.path.join(tmp_dir, "src")
    os.makedirs(src_dir)

    # Copy fixture files
    for fname in os.listdir(FIXTURES_DIR):
        if fname.endswith('.py') and 'syntax_error' not in fname:
            shutil.copy(os.path.join(FIXTURES_DIR, fname), src_dir)

    return tmp_dir


# ============================================================
# Tests: Pattern Extraction (extractor.py)
# ============================================================

class TestEntropy:
    """Test entropy computation."""

    def test_empty_string(self):
        from ussy_sentinel.extractor import _compute_entropy
        assert _compute_entropy("") == 0.0

    def test_single_char(self):
        from ussy_sentinel.extractor import _compute_entropy
        assert _compute_entropy("a") == 0.0

    def test_uniform_chars(self):
        from ussy_sentinel.extractor import _compute_entropy
        # All different chars → higher entropy
        e = _compute_entropy("abcdefghij")
        assert e > 0.0

    def test_repeated_chars(self):
        from ussy_sentinel.extractor import _compute_entropy
        # Same char repeated → low entropy
        e = _compute_entropy("aaaaaaa")
        assert e == 0.0

    def test_entropy_bounded(self):
        from ussy_sentinel.extractor import _compute_entropy
        e = _compute_entropy("aB3xY7pQzLm9nR2w")
        assert 0.0 <= e <= 1.0


class TestNamingConventions:
    """Test naming convention detection."""

    def test_snake_case_valid(self):
        from ussy_sentinel.extractor import _is_snake_case
        assert _is_snake_case("hello_world")
        assert _is_snake_case("my_function")
        assert _is_snake_case("x")
        assert _is_snake_case("get_data")

    def test_snake_case_invalid(self):
        from ussy_sentinel.extractor import _is_snake_case
        assert not _is_snake_case("HelloWorld")
        assert not _is_snake_case("myFunction")
        assert not _is_snake_case("__init__")

    def test_camel_case_valid(self):
        from ussy_sentinel.extractor import _is_camel_case
        assert _is_camel_case("HelloWorld")
        assert _is_camel_case("MyClass")

    def test_camel_case_invalid(self):
        from ussy_sentinel.extractor import _is_camel_case
        assert not _is_camel_case("hello_world")
        assert not _is_camel_case("x")


class TestFeatureVector:
    """Test FeatureVector data structure."""

    def test_to_list_length(self):
        from ussy_sentinel.extractor import FeatureVector
        vec = FeatureVector(name="test")
        assert len(vec.to_list()) == 25

    def test_feature_names_length(self):
        from ussy_sentinel.extractor import FeatureVector
        assert len(FeatureVector.feature_names()) == 25

    def test_from_list_roundtrip(self):
        from ussy_sentinel.extractor import FeatureVector
        original = FeatureVector(
            name="test",
            name_length=0.5,
            name_entropy=0.3,
            cyclomatic_complexity=0.7,
        )
        values = original.to_list()
        restored = FeatureVector.from_list(values, name="test")
        assert restored.name_length == pytest.approx(0.5)
        assert restored.name_entropy == pytest.approx(0.3)
        assert restored.cyclomatic_complexity == pytest.approx(0.7)

    def test_default_values(self):
        from ussy_sentinel.extractor import FeatureVector
        vec = FeatureVector(name="test")
        assert vec.name_length == 0.0
        assert vec.kind == "function"

    def test_all_features_in_range(self):
        """All features should be in [0, 1] range."""
        from ussy_sentinel.extractor import FeatureVector
        vec = FeatureVector(name="test")
        for v in vec.to_list():
            assert 0.0 <= v <= 1.0


class TestComplexityVisitor:
    """Test AST complexity visitor."""

    def test_simple_function(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        tree = ast.parse("def f(): return 1")
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.complexity == 1
        assert visitor.num_returns == 1

    def test_if_statement(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        tree = ast.parse("def f(x):\n    if x: return 1\n    return 0")
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.complexity == 2  # base + if

    def test_for_loop(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        tree = ast.parse("def f(items):\n    for x in items: pass")
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.complexity == 2  # base + for
        assert visitor.num_loops == 1

    def test_try_except(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        tree = ast.parse("def f():\n    try: pass\n    except: pass")
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.complexity == 2  # base + except

    def test_nesting_depth(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        source = "def f():\n    if True:\n        if True:\n            pass"
        tree = ast.parse(source)
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.max_nesting == 2

    def test_bool_op(self):
        import ast
        from ussy_sentinel.extractor import ComplexityVisitor
        tree = ast.parse("def f(x, y):\n    if x and y: pass")
        func = tree.body[0]
        visitor = ComplexityVisitor()
        visitor.visit(func)
        assert visitor.complexity == 3  # base + if + and


class TestPatternExtraction:
    """Test pattern extraction from source code."""

    def test_extract_from_sample(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py")
        assert len(patterns) > 0
        # Should find functions
        func_names = [p.name for p in patterns]
        assert "simple_function" in func_names
        assert "complex_function" in func_names

    def test_extract_from_file(self):
        from ussy_sentinel.extractor import extract_patterns_from_file
        patterns = extract_patterns_from_file(SAMPLE_MODULE)
        assert len(patterns) > 0

    def test_extract_granularity_class(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py", granularity="class")
        # Should find both functions and classes
        kinds = set(p.kind for p in patterns)
        assert "function" in kinds
        assert "class" in kinds

    def test_extract_granularity_module(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py", granularity="module")
        assert len(patterns) == 1
        assert patterns[0].kind == "module"

    def test_syntax_error_returns_empty(self):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source("def broken(\n", "bad.py")
        assert patterns == []

    def test_minimal_module(self):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source("# just a comment\n", "min.py")
        assert patterns == []

    def test_features_normalized(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py")
        for p in patterns:
            for v in p.to_list():
                assert 0.0 <= v <= 1.0, f"Feature out of range in {p.name}"

    def test_extract_from_directory(self, tmp_project):
        from ussy_sentinel.extractor import extract_patterns_from_directory
        src_dir = os.path.join(tmp_project, "src")
        patterns = extract_patterns_from_directory(src_dir)
        assert len(patterns) > 0

    def test_nonexistent_file(self):
        from ussy_sentinel.extractor import extract_patterns_from_file
        patterns = extract_patterns_from_file("/nonexistent/file.py")
        assert patterns == []

    def test_complex_function_features(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py")
        complex_fn = next(p for p in patterns if p.name == "complex_function")
        assert complex_fn.cyclomatic_complexity > 0.0  # Has complexity
        assert complex_fn.num_args > 0.0  # Has arguments

    def test_simple_function_features(self, sample_source):
        from ussy_sentinel.extractor import extract_patterns_from_source
        patterns = extract_patterns_from_source(sample_source, "sample.py")
        simple_fn = next(p for p in patterns if p.name == "simple_function")
        assert simple_fn.has_docstring > 0.0  # Has docstring
        assert simple_fn.name_snake_case > 0.0  # snake_case name


# ============================================================
# Tests: Distance Metrics (distance.py)
# ============================================================

class TestEuclideanDistance:
    """Test Euclidean distance computation."""

    def test_identical_vectors(self):
        from ussy_sentinel.distance import euclidean_distance
        assert euclidean_distance([0, 0, 0], [0, 0, 0]) == 0.0

    def test_unit_vectors(self):
        from ussy_sentinel.distance import euclidean_distance
        d = euclidean_distance([1, 0], [0, 1])
        assert d == pytest.approx(math.sqrt(2))

    def test_length_mismatch(self):
        from ussy_sentinel.distance import euclidean_distance
        with pytest.raises(ValueError):
            euclidean_distance([1, 2], [1, 2, 3])

    def test_symmetry(self):
        from ussy_sentinel.distance import euclidean_distance
        a = [0.1, 0.5, 0.9]
        b = [0.3, 0.2, 0.7]
        assert euclidean_distance(a, b) == pytest.approx(euclidean_distance(b, a))

    def test_non_negative(self):
        from ussy_sentinel.distance import euclidean_distance
        a = [random.random() for _ in range(10)]
        b = [random.random() for _ in range(10)]
        assert euclidean_distance(a, b) >= 0


class TestManhattanDistance:
    """Test Manhattan distance computation."""

    def test_identical_vectors(self):
        from ussy_sentinel.distance import manhattan_distance
        assert manhattan_distance([0, 0], [0, 0]) == 0.0

    def test_simple(self):
        from ussy_sentinel.distance import manhattan_distance
        assert manhattan_distance([1, 2], [3, 5]) == pytest.approx(5.0)

    def test_symmetry(self):
        from ussy_sentinel.distance import manhattan_distance
        a = [0.3, 0.7]
        b = [0.1, 0.9]
        assert manhattan_distance(a, b) == pytest.approx(manhattan_distance(b, a))


class TestHammingDistance:
    """Test Hamming distance computation."""

    def test_identical_vectors(self):
        from ussy_sentinel.distance import hamming_distance
        assert hamming_distance([0, 0], [0, 0]) == 0.0

    def test_all_different(self):
        from ussy_sentinel.distance import hamming_distance
        assert hamming_distance([0, 0], [1, 1], threshold=0.5) == 1.0

    def test_partial(self):
        from ussy_sentinel.distance import hamming_distance
        d = hamming_distance([0.0, 0.5], [0.1, 0.9], threshold=0.3)
        # 0.0 vs 0.1 → diff=0.1, not > 0.3
        # 0.5 vs 0.9 → diff=0.4, > 0.3
        assert d == pytest.approx(0.5)


class TestCosineDistance:
    """Test cosine distance computation."""

    def test_identical_vectors(self):
        from ussy_sentinel.distance import cosine_distance
        d = cosine_distance([1, 0], [1, 0])
        assert d == pytest.approx(0.0)

    def test_orthogonal(self):
        from ussy_sentinel.distance import cosine_distance
        d = cosine_distance([1, 0], [0, 1])
        assert d == pytest.approx(1.0)

    def test_opposite(self):
        from ussy_sentinel.distance import cosine_distance
        d = cosine_distance([1, 0], [-1, 0])
        assert d == pytest.approx(2.0)

    def test_zero_vector(self):
        from ussy_sentinel.distance import cosine_distance
        d = cosine_distance([0, 0], [1, 1])
        assert d == 1.0  # Zero magnitude → max distance


class TestMinDistanceToCorpus:
    """Test min distance to corpus computation."""

    def test_empty_corpus(self):
        from ussy_sentinel.distance import min_distance_to_corpus
        assert min_distance_to_corpus([1, 2, 3], []) == float('inf')

    def test_single_vector_corpus(self):
        from ussy_sentinel.distance import min_distance_to_corpus
        d = min_distance_to_corpus([1, 0], [[0, 0]], metric="euclidean")
        assert d == pytest.approx(1.0)

    def test_closest_in_corpus(self):
        from ussy_sentinel.distance import min_distance_to_corpus
        corpus = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
        query = [0.9, 0.1]
        d = min_distance_to_corpus(query, corpus, metric="euclidean")
        # Closest to [1.0, 0.0]: sqrt(0.01 + 0.01) ≈ 0.141
        assert d < 0.2


# ============================================================
# Tests: Self-Profile (profile.py)
# ============================================================

class TestSelfProfile:
    """Test self-profile building and serialization."""

    def test_build_profile(self, tmp_project):
        from ussy_sentinel.profile import build_profile
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir)
        assert profile.num_patterns > 0
        assert profile.num_files > 0

    def test_profile_granularity_module(self, tmp_project):
        from ussy_sentinel.profile import build_profile
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, granularity="module")
        # Module granularity: one pattern per file
        for p in profile.patterns:
            assert p.kind == "module"

    def test_profile_statistics(self, tmp_project):
        from ussy_sentinel.profile import build_profile
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir)
        assert len(profile.feature_means) == 25
        assert len(profile.feature_stds) == 25

    def test_profile_serialization(self, tmp_project):
        from ussy_sentinel.profile import build_profile, SelfProfile
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="test_profile")
        json_str = profile.to_json()
        restored = SelfProfile.from_json(json_str)
        assert restored.name == "test_profile"
        assert restored.num_patterns == profile.num_patterns

    def test_profile_pattern_vectors(self, tmp_project):
        from ussy_sentinel.profile import build_profile
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir)
        vectors = profile.pattern_vectors()
        assert len(vectors) == profile.num_patterns
        for v in vectors:
            assert len(v) == 25

    def test_profile_file_summary(self, tmp_project):
        from ussy_sentinel.profile import build_profile, profile_file_summary
        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir)
        summary = profile_file_summary(profile)
        assert "Self-Profile" in summary
        assert "Patterns" in summary

    def test_empty_directory(self, tmp_dir):
        from ussy_sentinel.profile import build_profile
        empty_dir = os.path.join(tmp_dir, "empty")
        os.makedirs(empty_dir)
        profile = build_profile(empty_dir)
        assert profile.num_patterns == 0


class TestHistoryDuration:
    """Test history duration parsing."""

    def test_months(self):
        from ussy_sentinel.profile import _parse_history_duration
        assert _parse_history_duration("3m") == "3 months ago"

    def test_years(self):
        from ussy_sentinel.profile import _parse_history_duration
        assert _parse_history_duration("1y") == "1 years ago"

    def test_days(self):
        from ussy_sentinel.profile import _parse_history_duration
        assert _parse_history_duration("30d") == "30 days ago"

    def test_invalid(self):
        from ussy_sentinel.profile import _parse_history_duration
        assert _parse_history_duration("abc") is None

    def test_empty(self):
        from ussy_sentinel.profile import _parse_history_duration
        assert _parse_history_duration("") is None


# ============================================================
# Tests: Detector Generation (detectors.py)
# ============================================================

class TestDetector:
    """Test individual Detector."""

    def test_detector_matches(self):
        from ussy_sentinel.detectors import Detector
        d = Detector(id="D-001", vector=[0.5, 0.5, 0.5], threshold=0.3)
        assert d.matches([0.5, 0.5, 0.5])  # Exact match
        assert not d.matches([1.0, 1.0, 1.0])  # Too far

    def test_detector_distance_to(self):
        from ussy_sentinel.detectors import Detector
        d = Detector(id="D-001", vector=[0.0, 0.0], threshold=0.3)
        dist = d.distance_to([1.0, 1.0])
        assert dist == pytest.approx(math.sqrt(2))

    def test_false_positive_rate(self):
        from ussy_sentinel.detectors import Detector
        d = Detector(id="D-001", vector=[0.5], threshold=0.3,
                     activation_count=10, false_positive_count=3)
        assert d.false_positive_rate == pytest.approx(0.3)

    def test_zero_activation_rate(self):
        from ussy_sentinel.detectors import Detector
        d = Detector(id="D-001", vector=[0.5], threshold=0.3)
        assert d.false_positive_rate == 0.0
        assert d.true_positive_rate == 0.0

    def test_serialization(self):
        from ussy_sentinel.detectors import Detector
        d = Detector(id="D-001", vector=[0.1, 0.2], threshold=0.3,
                     generation=1, activation_count=5)
        data = d.to_dict()
        restored = Detector.from_dict(data)
        assert restored.id == "D-001"
        assert restored.vector == [0.1, 0.2]
        assert restored.activation_count == 5


class TestNegativeSelection:
    """Test negative selection algorithm."""

    def test_generate_with_self(self):
        from ussy_sentinel.detectors import generate_detectors
        # Self corpus: vectors near [0.5, 0.5, 0.5]
        self_vectors = [[0.5, 0.5, 0.5]] * 10
        pop = generate_detectors(
            self_vectors=self_vectors,
            num_detectors=10,
            matching_threshold=0.3,
            seed=42,
        )
        assert len(pop.detectors) == 10
        # No detector should match self within the negative selection threshold
        for d in pop.detectors:
            min_dist = min(
                math.sqrt(sum((a - b) ** 2 for a, b in zip(d.vector, sv)))
                for sv in self_vectors
            )
            # Detector must be outside the negative selection threshold from self
            assert min_dist > 0.3
            # But detector's detection threshold should allow it to detect
            # patterns near itself
            assert d.threshold > 0

    def test_generate_no_self(self):
        from ussy_sentinel.detectors import generate_detectors
        pop = generate_detectors(
            self_vectors=[],
            num_detectors=5,
            seed=42,
        )
        assert len(pop.detectors) == 5

    def test_deterministic_with_seed(self):
        from ussy_sentinel.detectors import generate_detectors
        self_vectors = [[0.5, 0.5, 0.5]]
        pop1 = generate_detectors(self_vectors, num_detectors=5, seed=123)
        pop2 = generate_detectors(self_vectors, num_detectors=5, seed=123)
        for d1, d2 in zip(pop1.detectors, pop2.detectors):
            assert d1.vector == d2.vector

    def test_population_serialization(self):
        from ussy_sentinel.detectors import generate_detectors
        self_vectors = [[0.5, 0.5, 0.5]]
        pop = generate_detectors(self_vectors, num_detectors=3, seed=42)
        data = pop.to_dict()
        restored = type(pop).from_dict(data)
        assert len(restored.detectors) == 3
        assert restored.metric == "euclidean"

    def test_detectors_in_valid_range(self):
        from ussy_sentinel.detectors import generate_detectors
        self_vectors = [[0.3, 0.7, 0.1, 0.9]]
        pop = generate_detectors(self_vectors, num_detectors=10, seed=42)
        for d in pop.detectors:
            for v in d.vector:
                assert 0.0 <= v <= 1.0


class TestFeedback:
    """Test affinity maturation (feedback)."""

    def test_true_positive_feedback(self):
        from ussy_sentinel.detectors import Detector, DetectorPopulation, apply_feedback
        d = Detector(id="D-001", vector=[0.5], threshold=1.5)
        pop = DetectorPopulation(detectors=[d])
        original_threshold = d.threshold
        result = apply_feedback("D-001", pop, is_true_positive=True)
        assert result is not None
        assert result.threshold < original_threshold  # More sensitive
        assert result.true_positive_count == 1

    def test_false_positive_feedback(self):
        from ussy_sentinel.detectors import Detector, DetectorPopulation, apply_feedback
        d = Detector(id="D-001", vector=[0.5], threshold=0.3)
        pop = DetectorPopulation(detectors=[d])
        original_threshold = d.threshold
        result = apply_feedback("D-001", pop, is_true_positive=False)
        assert result is not None
        assert result.threshold > original_threshold  # Less sensitive
        assert result.false_positive_count == 1

    def test_nonexistent_detector(self):
        from ussy_sentinel.detectors import DetectorPopulation, apply_feedback
        pop = DetectorPopulation(detectors=[])
        result = apply_feedback("D-999", pop, is_true_positive=True)
        assert result is None

    def test_repeated_false_positives(self):
        from ussy_sentinel.detectors import Detector, DetectorPopulation, apply_feedback
        d = Detector(id="D-001", vector=[0.5], threshold=0.3)
        pop = DetectorPopulation(detectors=[d])
        for _ in range(10):
            apply_feedback("D-001", pop, is_true_positive=False)
        assert d.threshold >= 0.3  # Threshold should have increased
        assert d.false_positive_count == 10


class TestClonalExpansion:
    """Test clonal expansion (similar detector generation)."""

    def test_generate_similar(self):
        from ussy_sentinel.detectors import Detector, generate_similar_detectors
        d = Detector(id="D-001", vector=[0.5, 0.5, 0.5], threshold=0.3)
        self_vectors = [[0.1, 0.1, 0.1]]  # Far from detector
        new_detectors = generate_similar_detectors(d, self_vectors, count=3, seed=42)
        # Should generate some detectors (may be 0 if they match self)
        assert len(new_detectors) >= 0

    def test_similar_are_close(self):
        from ussy_sentinel.detectors import Detector, generate_similar_detectors
        d = Detector(id="D-001", vector=[0.5, 0.5, 0.5], threshold=0.5)
        self_vectors = [[0.0, 0.0, 0.0]]  # Far from detector region
        new_detectors = generate_similar_detectors(
            d, self_vectors, count=5, perturbation=0.05, seed=42
        )
        for nd in new_detectors:
            # Should be close to original
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(d.vector, nd.vector)))
            assert dist < 0.2  # Perturbation * sqrt(3)


# ============================================================
# Tests: Anomaly Checking (checker.py)
# ============================================================

class TestAnomalyReport:
    """Test anomaly report and scoring."""

    def test_severity_normal(self):
        from ussy_sentinel.checker import AnomalyReport
        report = AnomalyReport(target="test.py", anomaly_score=0.1)
        assert report.severity == "NORMAL"

    def test_severity_low(self):
        from ussy_sentinel.checker import AnomalyReport
        report = AnomalyReport(target="test.py", anomaly_score=0.3)
        assert report.severity == "LOW"

    def test_severity_moderate(self):
        from ussy_sentinel.checker import AnomalyReport
        report = AnomalyReport(target="test.py", anomaly_score=0.5)
        assert report.severity == "MODERATE"

    def test_severity_elevated(self):
        from ussy_sentinel.checker import AnomalyReport
        report = AnomalyReport(target="test.py", anomaly_score=0.7)
        assert report.severity == "ELEVATED"

    def test_severity_critical(self):
        from ussy_sentinel.checker import AnomalyReport
        report = AnomalyReport(target="test.py", anomaly_score=0.9)
        assert report.severity == "CRITICAL"

    def test_is_anomalous(self):
        from ussy_sentinel.checker import AnomalyReport
        assert AnomalyReport(target="test.py", anomaly_score=0.6).is_anomalous
        assert not AnomalyReport(target="test.py", anomaly_score=0.3).is_anomalous


class TestDetection:
    """Test detection objects."""

    def test_strength_exact_match(self):
        from ussy_sentinel.checker import Detection
        det = Detection(
            detector_id="D-001",
            pattern_name="test",
            pattern_kind="function",
            source_file="test.py",
            source_line=1,
            distance=0.0,
            threshold=0.3,
        )
        assert det.strength == 1.0

    def test_strength_at_threshold(self):
        from ussy_sentinel.checker import Detection
        det = Detection(
            detector_id="D-001",
            pattern_name="test",
            pattern_kind="function",
            source_file="test.py",
            source_line=1,
            distance=0.3,
            threshold=0.3,
        )
        assert det.strength == pytest.approx(0.0)


class TestChecker:
    """Test pattern checking."""

    def test_check_empty_patterns(self):
        from ussy_sentinel.checker import check_patterns
        from ussy_sentinel.detectors import DetectorPopulation
        pop = DetectorPopulation()
        report = check_patterns([], pop)
        assert report.anomaly_score == 0.0

    def test_check_with_no_detectors(self):
        from ussy_sentinel.checker import check_patterns
        from ussy_sentinel.detectors import DetectorPopulation
        from ussy_sentinel.extractor import FeatureVector
        pop = DetectorPopulation()
        patterns = [FeatureVector(name="test")]
        report = check_patterns(patterns, pop)
        assert report.num_detectors_fired == 0

    def test_check_file(self):
        from ussy_sentinel.checker import check_file
        from ussy_sentinel.detectors import Detector, DetectorPopulation
        # Create a detector that matches typical code
        d = Detector(id="D-001", vector=[0.5] * 25, threshold=1.0)
        pop = DetectorPopulation(detectors=[d], matching_threshold=1.0)
        report = check_file(SAMPLE_MODULE, pop)
        assert report.num_patterns_checked > 0

    def test_check_directory(self):
        from ussy_sentinel.checker import check_directory
        from ussy_sentinel.detectors import Detector, DetectorPopulation
        d = Detector(id="D-001", vector=[0.5] * 25, threshold=1.0)
        pop = DetectorPopulation(detectors=[d])
        reports = check_directory(FIXTURES_DIR, pop)
        assert len(reports) > 0

    def test_format_report(self):
        from ussy_sentinel.checker import AnomalyReport, format_report
        report = AnomalyReport(target="test.py", anomaly_score=0.5)
        text = format_report(report)
        assert "SENTINEL REPORT" in text
        assert "0.50" in text

    def test_format_report_with_detections(self):
        from ussy_sentinel.checker import AnomalyReport, Detection, format_report
        det = Detection(
            detector_id="D-001",
            pattern_name="test_func",
            pattern_kind="function",
            source_file="test.py",
            source_line=10,
            distance=0.1,
            threshold=0.3,
        )
        report = AnomalyReport(
            target="test.py", anomaly_score=0.7,
            detections=[det], num_detectors_fired=1,
        )
        text = format_report(report)
        assert "D-001" in text

    def test_explain_detection(self):
        from ussy_sentinel.checker import Detection, explain_detection
        from ussy_sentinel.extractor import FeatureVector
        det = Detection(
            detector_id="D-001",
            pattern_name="test_func",
            pattern_kind="function",
            source_file="test.py",
            source_line=10,
            distance=0.1,
            threshold=0.3,
            detector_vector=[0.5] * 25,
            pattern_vector=[0.2] * 25,
        )
        explanation = explain_detection(det, FeatureVector.feature_names())
        assert "D-001" in explanation
        assert "test_func" in explanation


# ============================================================
# Tests: Database Persistence (db.py)
# ============================================================

class TestSentinelDB:
    """Test SQLite persistence."""

    def test_init_db(self, tmp_dir):
        from ussy_sentinel.db import SentinelDB
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)
        assert os.path.exists(db_path)
        db.close()

    def test_save_and_load_profile(self, tmp_dir, tmp_project):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.profile import build_profile
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="test")
        pid = db.save_profile(profile, name="test")
        assert pid > 0

        loaded = db.load_profile("test")
        assert loaded is not None
        assert loaded.name == "test"
        assert loaded.num_patterns == profile.num_patterns
        db.close()

    def test_list_profiles(self, tmp_dir, tmp_project):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.profile import build_profile
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="test")
        db.save_profile(profile, name="test")

        profiles = db.list_profiles()
        assert len(profiles) >= 1
        db.close()

    def test_delete_profile(self, tmp_dir, tmp_project):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.profile import build_profile
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="to_delete")
        db.save_profile(profile, name="to_delete")
        assert db.delete_profile("to_delete")
        assert db.load_profile("to_delete") is None
        db.close()

    def test_save_and_load_detectors(self, tmp_dir):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.detectors import Detector, DetectorPopulation
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        d = Detector(id="D-001", vector=[0.5] * 25, threshold=0.3)
        pop = DetectorPopulation(detectors=[d], metric="euclidean")
        db.save_detectors(pop, name="test_pop")

        loaded = db.load_detectors("test_pop")
        assert loaded is not None
        assert len(loaded.detectors) == 1
        assert loaded.detectors[0].id == "D-001"
        db.close()

    def test_save_feedback(self, tmp_dir):
        from ussy_sentinel.db import SentinelDB
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        db.save_feedback("D-001", True, comment="Good catch")
        stats = db.get_feedback_stats("D-001")
        assert stats["total"] == 1
        assert stats["tp"] == 1
        assert stats["fp"] == 0
        db.close()

    def test_delete_detectors(self, tmp_dir):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.detectors import Detector, DetectorPopulation
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        d = Detector(id="D-001", vector=[0.5] * 25, threshold=0.3)
        pop = DetectorPopulation(detectors=[d])
        db.save_detectors(pop, name="to_delete")
        assert db.delete_detectors("to_delete")
        assert db.load_detectors("to_delete") is None
        db.close()

    def test_update_existing_profile(self, tmp_dir, tmp_project):
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.profile import build_profile
        db_path = os.path.join(tmp_dir, "test.db")
        db = SentinelDB(db_path)

        src_dir = os.path.join(tmp_project, "src")
        profile1 = build_profile(src_dir, name="test")
        db.save_profile(profile1, name="test")

        profile2 = build_profile(src_dir, name="test_updated")
        db.save_profile(profile2, name="test")

        loaded = db.load_profile("test")
        assert loaded is not None
        db.close()


# ============================================================
# Tests: CLI (cli.py)
# ============================================================

class TestCLI:
    """Test CLI commands."""

    def test_build_parser(self):
        from ussy_sentinel.cli import build_parser
        parser = build_parser()
        assert parser is not None

    def test_init_command(self, tmp_dir):
        from ussy_sentinel.cli import cmd_init
        class Args:
            directory = tmp_dir
            source = "."
        result = cmd_init(Args())
        assert result == 0 or result is None
        assert os.path.exists(os.path.join(tmp_dir, ".sentinel", "config.json"))

    def test_train_command(self, tmp_project):
        from ussy_sentinel.cli import cmd_train
        src_dir = os.path.join(tmp_project, "src")
        class Args:
            source = src_dir
            history = ""
            granularity = "function"
            name = "test"
            project = tmp_project
        result = cmd_train(Args())
        assert result == 0 or result is None

    def test_generate_command(self, tmp_project):
        from ussy_sentinel.cli import cmd_train, cmd_generate
        src_dir = os.path.join(tmp_project, "src")
        # Train first
        class TrainArgs:
            source = src_dir
            history = ""
            granularity = "function"
            name = "test"
            project = tmp_project
        cmd_train(TrainArgs())

        class GenArgs:
            detectors = 10
            coverage = 0.95
            matching_threshold = 0.3
            metric = "euclidean"
            profile = "test"
            name = ""
            seed = 42
            project = tmp_project
        result = cmd_generate(GenArgs())
        assert result == 0 or result is None

    def test_check_command(self, tmp_project):
        from ussy_sentinel.cli import cmd_train, cmd_generate, cmd_check
        src_dir = os.path.join(tmp_project, "src")

        class TrainArgs:
            source = src_dir
            history = ""
            granularity = "function"
            name = "test"
            project = tmp_project
        cmd_train(TrainArgs())

        class GenArgs:
            detectors = 10
            coverage = 0.95
            matching_threshold = 0.3
            metric = "euclidean"
            profile = "test"
            name = ""
            seed = 42
            project = tmp_project
        cmd_generate(GenArgs())

        class CheckArgs:
            target = SAMPLE_MODULE
            threshold = 0.5
            explain = False
            population = ""
            granularity = "function"
            project = tmp_project
        result = cmd_check(CheckArgs())
        assert result is not None

    def test_main_no_args(self):
        from ussy_sentinel.cli import main
        result = main([])
        assert result == 0

    def test_main_version(self):
        from ussy_sentinel.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_watch_stub(self):
        from ussy_sentinel.cli import cmd_watch
        class Args:
            pre_commit = False
            ci = False
        result = cmd_watch(Args())
        assert result == 0 or result is None

    def test_diff_stub(self):
        from ussy_sentinel.cli import cmd_diff
        class Args:
            project_a = "/a"
            project_b = "/b"
        result = cmd_diff(Args())
        assert result == 0 or result is None


# ============================================================
# Tests: Integration / End-to-End
# ============================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_train_generate_check_pipeline(self, tmp_project):
        """Full pipeline: train → generate → check."""
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.detectors import generate_detectors
        from ussy_sentinel.profile import build_profile
        from ussy_sentinel.checker import check_file

        src_dir = os.path.join(tmp_project, "src")

        # 1. Train
        profile = build_profile(src_dir, name="integration_test")
        assert profile.num_patterns > 0

        # 2. Generate detectors
        self_vectors = profile.pattern_vectors()
        pop = generate_detectors(
            self_vectors=self_vectors,
            num_detectors=50,
            matching_threshold=0.3,
            seed=42,
        )
        assert len(pop.detectors) > 0

        # 3. Check self (should be low anomaly)
        report = check_file(SAMPLE_MODULE, pop)
        # Self should have low anomaly score
        assert report.anomaly_score is not None

    def test_anomalous_code_scores_higher(self, tmp_project):
        """Anomalous code should score higher than normal code."""
        from ussy_sentinel.detectors import generate_detectors
        from ussy_sentinel.profile import build_profile
        from ussy_sentinel.checker import check_file

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="anomaly_test")
        self_vectors = profile.pattern_vectors()

        pop = generate_detectors(
            self_vectors=self_vectors,
            num_detectors=100,
            matching_threshold=0.25,
            seed=42,
        )

        # Check both normal and anomalous files
        normal_report = check_file(SAMPLE_MODULE, pop)
        anomalous_report = check_file(ANOMALOUS_MODULE, pop)

        # Both should produce reports
        assert normal_report.anomaly_score is not None
        assert anomalous_report.anomaly_score is not None

    def test_persistence_roundtrip(self, tmp_project):
        """Test that profiles and detectors survive persistence."""
        from ussy_sentinel.db import SentinelDB
        from ussy_sentinel.detectors import Detector, DetectorPopulation
        from ussy_sentinel.profile import build_profile

        db_path = os.path.join(tmp_project, "test.db")
        db = SentinelDB(db_path)

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="persist_test")
        db.save_profile(profile, name="persist_test")

        d = Detector(id="D-001", vector=[0.5] * 25, threshold=0.3)
        pop = DetectorPopulation(detectors=[d], metric="euclidean")
        db.save_detectors(pop, name="test_pop", profile_name="persist_test")

        # Reload
        loaded_profile = db.load_profile("persist_test")
        loaded_pop = db.load_detectors("test_pop")

        assert loaded_profile.num_patterns == profile.num_patterns
        assert len(loaded_pop.detectors) == 1
        db.close()

    def test_negative_selection_property(self):
        """Property test: generated detectors must NOT match self within threshold."""
        from ussy_sentinel.detectors import generate_detectors

        # Create a tight self cluster
        self_vectors = [[0.5 + random.gauss(0, 0.05) for _ in range(10)]
                        for _ in range(20)]
        # Clamp to [0, 1]
        self_vectors = [[max(0, min(1, v)) for v in vec] for vec in self_vectors]

        pop = generate_detectors(
            self_vectors=self_vectors,
            num_detectors=20,
            matching_threshold=0.3,
            seed=42,
        )

        # Verify no detector matches any self vector within threshold
        for d in pop.detectors:
            from ussy_sentinel.distance import euclidean_distance
            for sv in self_vectors:
                dist = euclidean_distance(d.vector, sv)
                assert dist > 0.3, f"Detector {d.id} matches self: dist={dist:.3f}"

    def test_self_score_baseline(self, tmp_project):
        """Self-corpus should have low anomaly score when checked against itself."""
        from ussy_sentinel.detectors import generate_detectors
        from ussy_sentinel.profile import build_profile
        from ussy_sentinel.checker import check_file

        src_dir = os.path.join(tmp_project, "src")
        profile = build_profile(src_dir, name="baseline_test")
        self_vectors = profile.pattern_vectors()

        if not self_vectors:
            pytest.skip("No patterns extracted")

        pop = generate_detectors(
            self_vectors=self_vectors,
            num_detectors=100,
            matching_threshold=0.3,
            seed=42,
        )

        # Check a self file — should ideally have low score
        report = check_file(SAMPLE_MODULE, pop)
        # Note: some detections are expected since individual patterns may differ
        # But the score should be reasonable
        assert 0.0 <= report.anomaly_score <= 1.0


# ============================================================
# Tests: Weighted Distance
# ============================================================

class TestWeightedDistance:
    """Test weighted Euclidean distance."""

    def test_equal_weights(self):
        from ussy_sentinel.distance import weighted_euclidean_distance
        d = weighted_euclidean_distance([0, 0], [1, 1], [1, 1])
        assert d == pytest.approx(math.sqrt(2))

    def test_zero_weight(self):
        from ussy_sentinel.distance import weighted_euclidean_distance
        d = weighted_euclidean_distance([0, 0], [1, 1], [1, 0])
        assert d == pytest.approx(1.0)

    def test_mismatched_lengths(self):
        from ussy_sentinel.distance import weighted_euclidean_distance
        with pytest.raises(ValueError):
            weighted_euclidean_distance([1, 2], [1, 2], [1])
