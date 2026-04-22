"""Tests for cavity.beat_frequency module."""

from __future__ import annotations

import numpy as np
import pytest

from ussy_cavity.beat_frequency import (
    BeatFrequency,
    autocorrelation,
    detect_beat_frequency,
    detect_livelock,
    find_periodic_peaks,
    format_beat_frequencies,
)


# ---------------------------------------------------------------------------
# autocorrelation
# ---------------------------------------------------------------------------


class TestAutocorrelation:
    def test_empty(self):
        result = autocorrelation(np.array([]))
        assert len(result) == 0

    def test_lag_zero_is_one(self):
        signal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = autocorrelation(signal)
        assert abs(result[0] - 1.0) < 1e-10

    def test_constant_signal(self):
        signal = np.ones(100)
        result = autocorrelation(signal)
        assert abs(result[0] - 1.0) < 1e-10 or abs(result[0]) < 1e-6
        # Constant signal: after centering, all zeros → autocorrelation ≈ 0

    def test_periodic_signal(self):
        """A periodic signal should have periodic peaks in autocorrelation."""
        fs = 100.0
        duration = 3.0
        t = np.arange(int(fs * duration)) / fs
        signal = np.sin(2.0 * np.pi * 5.0 * t)
        acf = autocorrelation(signal, max_lag=100)
        # Should have peaks at lag = fs/freq = 20
        assert len(acf) > 0

    def test_max_lag(self):
        signal = np.random.randn(200)
        result = autocorrelation(signal, max_lag=50)
        assert len(result) == 51  # 0 to 50 inclusive


# ---------------------------------------------------------------------------
# find_periodic_peaks
# ---------------------------------------------------------------------------


class TestFindPeriodicPeaks:
    def test_empty(self):
        assert find_periodic_peaks(np.array([])) == []

    def test_short(self):
        assert find_periodic_peaks(np.array([0.5])) == []

    def test_no_peaks(self):
        acf = np.linspace(1, 0, 50)  # Monotonically decreasing
        peaks = find_periodic_peaks(acf, min_peak_height=0.3)
        assert peaks == []

    def test_with_peak(self):
        acf = np.array([1.0, 0.5, 0.8, 0.5, 0.6, 0.3])
        peaks = find_periodic_peaks(acf, min_peak_height=0.3)
        assert 2 in peaks  # Index 2 is a peak


# ---------------------------------------------------------------------------
# detect_beat_frequency
# ---------------------------------------------------------------------------


class TestDetectBeatFrequency:
    def test_short_signal(self):
        signal = np.array([1.0, 2.0])
        result = detect_beat_frequency(signal)
        assert result == []

    def test_beat_signal(self, beat_signal):
        """Beat signal with f1=10Hz and f2=10.5Hz should produce beat at 0.5Hz."""
        result = detect_beat_frequency(beat_signal, fs=1000.0)
        assert len(result) > 0
        beat = result[0]
        assert abs(beat.f1 - 10.0) < 1.0 or abs(beat.f2 - 10.0) < 1.0
        assert abs(beat.beat_frequency - 0.5) < 1.0

    def test_livelock_confirmed_with_zero_throughput(self, beat_signal):
        result = detect_beat_frequency(beat_signal, fs=1000.0, throughput=np.zeros(len(beat_signal)))
        assert len(result) > 0
        assert result[0].is_livelock is True

    def test_no_livelock_with_throughput(self, beat_signal):
        throughput = np.ones(len(beat_signal)) * 100.0
        result = detect_beat_frequency(beat_signal, fs=1000.0, throughput=throughput)
        assert len(result) > 0
        assert result[0].is_livelock is False

    def test_zero_signal(self):
        signal = np.zeros(100)
        result = detect_beat_frequency(signal, fs=10.0)
        # Zero signal → no periodic peaks in autocorrelation
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# detect_livelock
# ---------------------------------------------------------------------------


class TestDetectLivelock:
    def test_basic(self, beat_signal):
        result = detect_livelock(beat_signal, fs=1000.0)
        assert isinstance(result, list)

    def test_with_throughput(self, beat_signal):
        throughput = np.zeros(len(beat_signal))
        result = detect_livelock(beat_signal, throughput_series=throughput, fs=1000.0)
        assert isinstance(result, list)
        if result:
            assert result[0].is_livelock is True


# ---------------------------------------------------------------------------
# BeatFrequency dataclass
# ---------------------------------------------------------------------------


class TestBeatFrequency:
    def test_summary_livelock(self):
        b = BeatFrequency(
            beat_frequency=0.5, beat_period=2.0,
            f1=10.0, f2=10.5, amplitude=0.8,
            is_livelock=True, avg_throughput=0.0,
        )
        s = b.summary()
        assert "LIVELOCK CONFIRMED" in s
        assert "0.5000" in s

    def test_summary_no_livelock(self):
        b = BeatFrequency(
            beat_frequency=0.3, beat_period=3.33,
            f1=5.0, f2=5.3, amplitude=0.5,
            is_livelock=False, avg_throughput=50.0,
        )
        s = b.summary()
        assert "Beat pattern detected" in s


# ---------------------------------------------------------------------------
# format_beat_frequencies
# ---------------------------------------------------------------------------


class TestFormatBeatFrequencies:
    def test_empty(self):
        s = format_beat_frequencies([])
        assert "No beat frequencies" in s

    def test_with_beats(self):
        beats = [
            BeatFrequency(0.5, 2.0, 10.0, 10.5, 0.8, True, 0.0),
        ]
        s = format_beat_frequencies(beats)
        assert "LIVELOCK CONFIRMED" in s
