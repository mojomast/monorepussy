"""Beat frequency livelock detection.

Detects livelocks by identifying amplitude modulation (beat patterns)
in wait-duration signals — where two competing processes create periodic
constructive/destructive interference.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BeatFrequency:
    """A detected beat frequency (livelock signature)."""

    beat_frequency: float  # Hz — the livelock period
    beat_period: float  # seconds — time between contention spikes
    f1: float  # First competing frequency
    f2: float  # Second competing frequency
    amplitude: float  # Beat amplitude (severity)
    is_livelock: bool  # Whether livelock conditions are confirmed
    avg_throughput: float  # Average throughput during analysis window

    def summary(self) -> str:
        status = "LIVELOCK CONFIRMED" if self.is_livelock else "Beat pattern detected"
        return (
            f"{status}: beat_f={self.beat_frequency:.4f}Hz "
            f"(period={self.beat_period:.2f}s), "
            f"f1={self.f1:.4f}Hz, f2={self.f2:.4f}Hz, "
            f"amplitude={self.amplitude:.2f}, "
            f"avg_throughput={self.avg_throughput:.2f}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def autocorrelation(signal: np.ndarray, max_lag: int | None = None) -> np.ndarray:
    """Compute the normalized autocorrelation of a signal.

    Parameters
    ----------
    signal : np.ndarray
        1-D input signal.
    max_lag : int or None
        Maximum lag to compute.  Defaults to len(signal) // 2.

    Returns
    -------
    np.ndarray
        Autocorrelation values for lags 0, 1, …, max_lag.
    """
    n = len(signal)
    if n == 0:
        return np.array([])

    if max_lag is None:
        max_lag = n // 2

    max_lag = min(max_lag, n - 1)

    # Zero-mean
    centered = signal - np.mean(signal)
    var = np.sum(centered ** 2)

    if var < 1e-15:
        return np.zeros(max_lag + 1)

    result = np.zeros(max_lag + 1)
    for lag in range(max_lag + 1):
        result[lag] = np.sum(centered[:n - lag] * centered[lag:]) / var

    return result


def find_periodic_peaks(acf: np.ndarray, min_peak_height: float = 0.3) -> list[int]:
    """Find periodic peaks in an autocorrelation function.

    Returns list of lag indices where peaks occur.
    """
    if len(acf) < 3:
        return []

    peaks: list[int] = []
    for i in range(1, len(acf) - 1):
        if acf[i] > acf[i - 1] and acf[i] > acf[i + 1] and acf[i] > min_peak_height:
            peaks.append(i)
    return peaks


def detect_beat_frequency(
    signal: np.ndarray,
    fs: float = 1.0,
    throughput: np.ndarray | None = None,
) -> list[BeatFrequency]:
    """Detect beat frequencies (livelock signatures) in a signal.

    Parameters
    ----------
    signal : np.ndarray
        Wait-duration time series.
    fs : float
        Sampling frequency (Hz).
    throughput : np.ndarray or None
        Throughput time series.  If average throughput ≈ 0, livelock is confirmed.

    Returns
    -------
    list[BeatFrequency]
    """
    if len(signal) < 8:
        return []

    # Compute autocorrelation
    acf = autocorrelation(signal, max_lag=len(signal) // 2)

    # Find periodic peaks in autocorrelation
    periodic_lags = find_periodic_peaks(acf)
    if not periodic_lags:
        return []

    # Compute spectral density to find competing frequencies
    n = len(signal)
    spectrum = np.abs(np.fft.rfft(signal - np.mean(signal)))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)

    # Find top 2 spectral peaks (excluding DC)
    if len(spectrum) < 3:
        return []

    # Skip DC component (index 0)
    spec_magnitude = spectrum[1:]
    spec_freqs = freqs[1:]

    # Find the two largest peaks
    top_indices = np.argsort(spec_magnitude)[-2:][::-1]
    f1 = float(spec_freqs[top_indices[0]]) if len(top_indices) >= 1 else 0.0
    f2 = float(spec_freqs[top_indices[1]]) if len(top_indices) >= 2 else 0.0

    # Beat frequency = |f1 - f2|
    beat_f = abs(f1 - f2)
    if beat_f < 1e-12:
        return []

    beat_period = 1.0 / beat_f if beat_f > 1e-12 else float("inf")

    # Amplitude from autocorrelation peak
    amplitude = float(acf[periodic_lags[0]])

    # Determine average throughput
    avg_throughput = 0.0
    if throughput is not None and len(throughput) > 0:
        avg_throughput = float(np.mean(throughput))

    # Livelock confirmed if beat exists AND throughput ≈ 0
    is_livelock = avg_throughput < 1e-6

    return [
        BeatFrequency(
            beat_frequency=beat_f,
            beat_period=beat_period,
            f1=f1,
            f2=f2,
            amplitude=amplitude,
            is_livelock=is_livelock,
            avg_throughput=avg_throughput,
        )
    ]


def detect_livelock(
    wait_time_series: np.ndarray,
    throughput_series: np.ndarray | None = None,
    fs: float = 1.0,
) -> list[BeatFrequency]:
    """High-level livelock detection from wait and throughput time series.

    Parameters
    ----------
    wait_time_series : np.ndarray
        1-D array of total wait duration per time step.
    throughput_series : np.ndarray or None
        1-D array of throughput (items completed) per time step.
    fs : float
        Sampling frequency (Hz).

    Returns
    -------
    list[BeatFrequency]
        Detected beat patterns, with livelock flag set where throughput ≈ 0.
    """
    return detect_beat_frequency(wait_time_series, fs, throughput_series)


def format_beat_frequencies(beats: list[BeatFrequency]) -> str:
    """Format beat frequencies into a human-readable string."""
    lines: list[str] = []
    if not beats:
        lines.append("No beat frequencies (livelocks) detected.")
        return "\n".join(lines)

    lines.append(f"Beat Frequency Analysis ({len(beats)} pattern(s) found)")
    lines.append("=" * 60)
    for beat in beats:
        lines.append(beat.summary())
    return "\n".join(lines)
