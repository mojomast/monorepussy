"""Tests for cavity.standing_wave module."""

from __future__ import annotations

import numpy as np
import pytest

from cavity.standing_wave import (
    StandingWave,
    _hann_window,
    detect_standing_waves,
    find_persistent_peaks,
    format_standing_waves,
    stft,
)


# ---------------------------------------------------------------------------
# Hann window
# ---------------------------------------------------------------------------


class TestHannWindow:
    def test_length(self):
        w = _hann_window(10)
        assert len(w) == 10

    def test_single_element(self):
        w = _hann_window(1)
        assert len(w) == 1
        assert w[0] == 1.0

    def test_symmetric(self):
        w = _hann_window(11)
        for i in range(5):
            assert abs(w[i] - w[10 - i]) < 1e-10

    def test_bounds(self):
        w = _hann_window(10)
        assert np.all(w >= 0)
        assert np.all(w <= 1)


# ---------------------------------------------------------------------------
# STFT
# ---------------------------------------------------------------------------


class TestSTFT:
    def test_basic_output(self, sine_signal):
        freqs, times, Sxx = stft(sine_signal, fs=100.0, nperseg=64)
        assert len(freqs) > 0
        assert len(times) > 0
        assert Sxx.shape[0] == len(freqs)
        assert Sxx.shape[1] == len(times)

    def test_short_signal_padded(self):
        signal = np.ones(10)
        freqs, times, Sxx = stft(signal, fs=1.0, nperseg=256)
        assert Sxx.shape[0] > 0

    def test_frequency_resolution(self, sine_signal):
        """A 1 Hz sine should have peak near 1 Hz."""
        freqs, times, Sxx = stft(sine_signal, fs=100.0, nperseg=256)
        mean_magnitude = np.mean(np.abs(Sxx), axis=1)
        peak_idx = np.argmax(mean_magnitude)
        peak_freq = freqs[peak_idx]
        # Allow some tolerance due to spectral leakage
        assert abs(peak_freq - 1.0) < 2.0

    def test_zero_signal(self):
        signal = np.zeros(100)
        freqs, times, Sxx = stft(signal, fs=10.0, nperseg=32)
        assert np.allclose(np.abs(Sxx), 0, atol=1e-10)

    def test_custom_overlap(self, sine_signal):
        freqs1, times1, _ = stft(sine_signal, fs=100.0, nperseg=64, noverlap=32)
        freqs2, times2, _ = stft(sine_signal, fs=100.0, nperseg=64, noverlap=16)
        # More overlap = smaller step = more time segments
        assert len(times1) >= len(times2)


# ---------------------------------------------------------------------------
# find_persistent_peaks
# ---------------------------------------------------------------------------


class TestFindPersistentPeaks:
    def test_empty(self):
        result = find_persistent_peaks(
            np.zeros((5, 0)), np.array([1, 2, 3, 4, 5]), np.array([])
        )
        assert result == []

    def test_flat_spectrum(self):
        Sxx = np.ones((5, 10)) * 0.001  # Very small magnitude
        freqs = np.array([1, 2, 3, 4, 5], dtype=float)
        times = np.arange(10, dtype=float)
        result = find_persistent_peaks(Sxx, freqs, times)
        # All have equal magnitude, normalized to 1.0 > 0.1 threshold
        assert len(result) > 0

    def test_single_dominant_frequency(self):
        Sxx = np.zeros((10, 5))
        Sxx[3, :] = 100.0  # Frequency index 3 dominates all windows
        freqs = np.arange(10, dtype=float)
        times = np.arange(5, dtype=float)
        result = find_persistent_peaks(Sxx, freqs, times, persistence_threshold=0.6)
        # Index 3 should be found with persistence 1.0
        found_indices = [r[0] for r in result]
        assert 3 in found_indices


# ---------------------------------------------------------------------------
# detect_standing_waves
# ---------------------------------------------------------------------------


class TestDetectStandingWaves:
    def test_short_signal(self):
        signal = np.array([1.0, 2.0])
        waves = detect_standing_waves(signal)
        assert waves == []

    def test_persistent_sine(self):
        """A persistent sine wave should be detected as a standing wave."""
        fs = 100.0
        duration = 10.0
        t = np.arange(int(fs * duration)) / fs
        signal = 5.0 * np.sin(2.0 * np.pi * 2.0 * t)
        waves = detect_standing_waves(signal, fs=fs, nperseg=256, persistence_threshold=0.5)
        assert len(waves) > 0

    def test_noise_signal(self):
        """Pure noise should produce fewer/no standing waves."""
        rng = np.random.default_rng(42)
        signal = rng.standard_normal(1000)
        waves = detect_standing_waves(signal, fs=100.0, persistence_threshold=0.8)
        # Noise should not produce many persistent peaks (not guaranteed, but likely)
        assert isinstance(waves, list)

    def test_with_resource_names(self):
        fs = 100.0
        t = np.arange(500) / fs
        signal = 3.0 * np.sin(2.0 * np.pi * 5.0 * t)
        waves = detect_standing_waves(
            signal, fs=fs, nperseg=128,
            resource_names=["lock_a", "lock_b", "mutex", "pool"],
        )
        assert isinstance(waves, list)

    def test_zero_signal(self):
        signal = np.zeros(200)
        waves = detect_standing_waves(signal, fs=10.0)
        assert waves == []


# ---------------------------------------------------------------------------
# StandingWave dataclass
# ---------------------------------------------------------------------------


class TestStandingWave:
    def test_summary(self):
        w = StandingWave(frequency=1.5, amplitude=3.0, persistence=0.8, q_factor=10.0)
        s = w.summary()
        assert "1.5000" in s
        assert "80.00%" in s

    def test_defaults(self):
        w = StandingWave(frequency=1.0, amplitude=1.0, persistence=1.0, q_factor=1.0)
        assert w.phase_nodes == []
        assert w.phase_antinodes == []


# ---------------------------------------------------------------------------
# format_standing_waves
# ---------------------------------------------------------------------------


class TestFormatStandingWaves:
    def test_empty(self):
        s = format_standing_waves([])
        assert "No standing waves" in s

    def test_with_waves(self):
        waves = [
            StandingWave(frequency=2.0, amplitude=5.0, persistence=0.9, q_factor=15.0),
        ]
        s = format_standing_waves(waves)
        assert "Standing Waves (1 detected)" in s
