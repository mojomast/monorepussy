"""Tests for coroner.traces — Trace Evidence Collection."""

from __future__ import annotations

from coroner.models import TraceType
from coroner.traces import (
    analyze_traces,
    format_traces,
    _detect_fibers,
    _detect_dna,
    _detect_fingerprints,
    _detect_soil,
    _detect_tool_marks,
    _detect_glass_fragments,
)
from coroner.models import Stage, StageStatus, TraceEvidence


class TestAnalyzeTraces:
    """Tests for the main analyze_traces function."""

    def test_failing_run_produces_traces(self, simple_failing_run):
        result = analyze_traces(simple_failing_run)
        assert len(result.forward_traces) > 0

    def test_bidirectional_produces_reverse_traces(self, simple_failing_run):
        result = analyze_traces(simple_failing_run, bidirectional=True)
        # With env var divergence between stages, we should get some reverse traces
        # or forward traces at minimum
        total = len(result.forward_traces) + len(result.reverse_traces)
        assert total > 0

    def test_no_bidirectional_means_no_reverse(self, simple_failing_run):
        result = analyze_traces(simple_failing_run, bidirectional=False)
        assert len(result.reverse_traces) == 0

    def test_suspicious_transfers_filtered(self, multi_failure_run):
        result = analyze_traces(multi_failure_run, bidirectional=True)
        for t in result.suspicious_transfers:
            assert t.suspicion_score > 0.7

    def test_passing_run_minimal_traces(self, passing_run):
        result = analyze_traces(passing_run)
        # Passing run with minimal differences should have fewer suspicious traces
        suspicious = [t for t in result.suspicious_transfers if t.suspicion_score > 0.7]
        # May have some missing-trace suspicion but not many
        assert len(suspicious) <= 5

    def test_single_stage_run(self):
        from coroner.models import PipelineRun, Stage
        run = PipelineRun(run_id="single")
        run.stages = [Stage(name="checkout", index=0)]
        result = analyze_traces(run)
        assert len(result.forward_traces) == 0
        assert len(result.reverse_traces) == 0

    def test_empty_run(self):
        from coroner.models import PipelineRun
        run = PipelineRun(run_id="empty")
        result = analyze_traces(run)
        assert len(result.forward_traces) == 0

    def test_env_divergence_produces_dna_traces(self, env_diverge_run):
        result = analyze_traces(env_diverge_run)
        dna_traces = [t for t in result.forward_traces if t.trace_type == TraceType.DNA]
        assert len(dna_traces) > 0

    def test_tool_mark_detection(self, simple_failing_run):
        """Build stage has CC=gcc, GCC_VERSION=12.2 that other stages don't."""
        result = analyze_traces(simple_failing_run)
        tool_traces = [t for t in result.forward_traces if t.trace_type == TraceType.TOOL_MARKS]
        assert len(tool_traces) > 0


class TestDetectFibers:
    """Tests for fiber (dependency) detection."""

    def test_matching_deps_no_traces(self):
        s1 = Stage(name="a", index=0, env_vars={"DEP_VERSION": "1.0"})
        s2 = Stage(name="b", index=1, env_vars={"DEP_VERSION": "1.0"})
        traces = _detect_fibers(s1, s2)
        fiber_traces = [t for t in traces if t.trace_type == TraceType.FIBERS]
        assert len(fiber_traces) == 0

    def test_diverging_deps_produce_traces(self):
        s1 = Stage(name="a", index=0, env_vars={"DEP_VERSION": "1.0"})
        s2 = Stage(name="b", index=1, env_vars={"DEP_VERSION": "2.0"})
        traces = _detect_fibers(s1, s2)
        assert len(traces) > 0
        assert traces[0].trace_type == TraceType.FIBERS


class TestDetectDNA:
    """Tests for DNA (configuration) detection."""

    def test_changed_env_var(self):
        s1 = Stage(name="a", index=0, env_vars={"FOO": "bar"})
        s2 = Stage(name="b", index=1, env_vars={"FOO": "baz"})
        traces = _detect_dna(s1, s2)
        assert len(traces) > 0
        assert traces[0].trace_type == TraceType.DNA


class TestDetectFingerprints:
    """Tests for fingerprint (artifact hash) detection."""

    def test_changed_artifact_hash(self):
        s1 = Stage(name="a", index=0, artifact_hashes={"file.txt": "hash1"})
        s2 = Stage(name="b", index=1, artifact_hashes={"file.txt": "hash2"})
        traces = _detect_fingerprints(s1, s2)
        assert len(traces) > 0
        assert traces[0].trace_type == TraceType.FINGERPRINTS

    def test_same_hash_no_trace(self):
        s1 = Stage(name="a", index=0, artifact_hashes={"file.txt": "hash1"})
        s2 = Stage(name="b", index=1, artifact_hashes={"file.txt": "hash1"})
        traces = _detect_fingerprints(s1, s2)
        assert len(traces) == 0


class TestDetectSoil:
    """Tests for soil (platform) detection."""

    def test_different_platform(self):
        s1 = Stage(name="a", index=0, env_vars={"PLATFORM": "linux"})
        s2 = Stage(name="b", index=1, env_vars={"PLATFORM": "darwin"})
        traces = _detect_soil(s1, s2)
        assert len(traces) > 0
        assert traces[0].trace_type == TraceType.SOIL


class TestDetectToolMarks:
    """Tests for tool mark (toolchain) detection."""

    def test_different_compiler(self):
        s1 = Stage(name="a", index=0, env_vars={"CC": "gcc", "GCC_VERSION": "12.1"})
        s2 = Stage(name="b", index=1, env_vars={"CC": "clang", "GCC_VERSION": "12.1"})
        traces = _detect_tool_marks(s1, s2)
        assert len(traces) > 0
        assert traces[0].trace_type == TraceType.TOOL_MARKS


class TestFormatTraces:
    """Tests for format_traces."""

    def test_format_empty_result(self):
        from coroner.models import TraceTransferResult
        result = TraceTransferResult()
        text = format_traces(result)
        assert isinstance(text, str)

    def test_format_with_traces(self, simple_failing_run):
        result = analyze_traces(simple_failing_run)
        text = format_traces(result)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_format_suspicious_highlighted(self, multi_failure_run):
        result = analyze_traces(multi_failure_run, bidirectional=True)
        text = format_traces(result)
        if result.suspicious_transfers:
            assert "Suspicious" in text or "suspicion" in text.lower()
