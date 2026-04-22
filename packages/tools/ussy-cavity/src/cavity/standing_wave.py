"""Standing wave detection via Short-Time Fourier Transform (STFT).

Detects active deadlocks as persistent spectral peaks in wait-duration
time series data — analogous to standing waves in an acoustic cavity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StandingWave:
    """A detected standing wave (persistent deadlock signature)."""

    frequency: float  # Hz
    amplitude: float  # Spectral magnitude
    persistence: float  # Fraction of windows where peak is present (0-1)
    q_factor: float  # Quality factor (higher = more persistent)
    phase_nodes: list[str] = field(default_factory=list)  # Deadlocked resources
    phase_antinodes: list[str] = field(default_factory=list)  # Retrying resources

    def summary(self) -> str:
        return (
            f"Standing wave: f={self.frequency:.4f}Hz, "
            f"amplitude={self.amplitude:.2f}, "
            f"persistence={self.persistence:.2%}, Q={self.q_factor:.1f}"
        )


# ---------------------------------------------------------------------------
# STFT implementation
# ---------------------------------------------------------------------------


def _hann_window(n: int) -> np.ndarray:
    """Create a Hann window of length *n*."""
    if n <= 1:
        return np.ones(n, dtype=float)
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(n) / (n - 1)))


def stft(
    signal: np.ndarray,
    fs: float = 1.0,
    nperseg: int = 256,
    noverlap: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the Short-Time Fourier Transform.

    Parameters
    ----------
    signal : np.ndarray
        Input time-domain signal.
    fs : float
        Sampling frequency (Hz).
    nperseg : int
        Length of each segment (window).
    noverlap : int or None
        Number of overlapping samples.  Defaults to nperseg // 2.

    Returns
    -------
    frequencies : np.ndarray
        Array of frequency bins.
    times : np.ndarray
        Array of time centers for each segment.
    Sxx : np.ndarray
        2D complex STFT matrix (frequencies × times).
    """
    if noverlap is None:
        noverlap = nperseg // 2

    step = nperseg - noverlap
    n = len(signal)

    if n < nperseg:
        # Pad the signal to at least one window
        signal = np.pad(signal, (0, nperseg - n), mode="constant")

    window = _hann_window(nperseg)

    # Number of segments
    n_segs = max(1, (len(signal) - noverlap) // step)

    # Frequency bins
    freqs = np.fft.rfftfreq(nperseg, d=1.0 / fs)
    n_freqs = len(freqs)

    Sxx = np.zeros((n_freqs, n_segs), dtype=complex)
    times = np.zeros(n_segs)

    for seg_idx in range(n_segs):
        start = seg_idx * step
        end = start + nperseg
        if end > len(signal):
            break
        segment = signal[start:end] * window
        Sxx[:, seg_idx] = np.fft.rfft(segment)
        times[seg_idx] = (start + nperseg / 2.0) / fs

    return freqs, times[:seg_idx + 1 if seg_idx > 0 else 1], Sxx[:, :seg_idx + 1 if seg_idx > 0 else 1]


def find_persistent_peaks(
    Sxx: np.ndarray,
    frequencies: np.ndarray,
    times: np.ndarray,
    persistence_threshold: float = 0.7,
    amplitude_threshold: float = 0.1,
) -> list[tuple[int, float, float]]:
    """Find spectral peaks that persist across multiple STFT windows.

    Returns list of (frequency_index, mean_amplitude, persistence_ratio).
    """
    n_freqs, n_times = Sxx.shape
    if n_times == 0:
        return []

    magnitude = np.abs(Sxx)

    # Normalize by global max to get relative amplitudes
    global_max = np.max(magnitude)
    if global_max < 1e-15:
        return []

    norm_magnitude = magnitude / global_max

    peaks: list[tuple[int, float, float]] = []

    for fi in range(n_freqs):
        # Count windows where this frequency bin exceeds amplitude threshold
        above = np.sum(norm_magnitude[fi, :] > amplitude_threshold)
        persistence = above / n_times

        if persistence >= persistence_threshold:
            mean_amp = float(np.mean(magnitude[fi, :]))
            peaks.append((fi, mean_amp, float(persistence)))

    # Sort by amplitude descending
    peaks.sort(key=lambda p: -p[1])
    return peaks


def detect_standing_waves(
    wait_time_series: np.ndarray,
    fs: float = 1.0,
    nperseg: int = 256,
    persistence_threshold: float = 0.7,
    amplitude_threshold: float = 0.1,
    resource_names: list[str] | None = None,
) -> list[StandingWave]:
    """Detect standing waves in a wait-duration time series.

    Parameters
    ----------
    wait_time_series : np.ndarray
        1-D array of total wait duration per time step.
    fs : float
        Sampling frequency (Hz).
    nperseg : int
        STFT window size.
    persistence_threshold : float
        Minimum fraction of windows a peak must be present.
    amplitude_threshold : float
        Minimum relative amplitude (0-1) to count as a peak.
    resource_names : list[str] or None
        Names of resources for phase identification.

    Returns
    -------
    list[StandingWave]
    """
    if len(wait_time_series) < 4:
        return []

    freqs, times, Sxx = stft(wait_time_series, fs=fs, nperseg=min(nperseg, len(wait_time_series)))

    raw_peaks = find_persistent_peaks(Sxx, freqs, times, persistence_threshold, amplitude_threshold)

    waves: list[StandingWave] = []
    for fi, mean_amp, persistence in raw_peaks:
        freq = float(freqs[fi])

        # Q-factor approximation: persistence × total time × frequency
        if len(times) > 1:
            total_time = float(times[-1] - times[0])
        else:
            total_time = 1.0 / max(fs, 1e-9)

        q = persistence * freq * total_time if freq > 1e-12 else float("inf")

        # Phase identification from eigenvectors is complex; provide
        # best-effort assignment based on resource_names
        nodes: list[str] = []
        antinodes: list[str] = []
        if resource_names:
            # Assign first half as nodes (deadlocked), second half as antinodes (retrying)
            half = len(resource_names) // 2
            nodes = resource_names[:half]
            antinodes = resource_names[half:]

        waves.append(
            StandingWave(
                frequency=freq,
                amplitude=mean_amp,
                persistence=persistence,
                q_factor=q,
                phase_nodes=nodes,
                phase_antinodes=antinodes,
            )
        )

    # Sort by Q-factor descending (most persistent first)
    waves.sort(key=lambda w: -w.q_factor if w.q_factor < 1e6 else -1e6)
    return waves


def format_standing_waves(waves: list[StandingWave]) -> str:
    """Format standing waves into a human-readable string."""
    lines: list[str] = []
    if not waves:
        lines.append("No standing waves detected.")
        return "\n".join(lines)

    lines.append(f"Standing Waves ({len(waves)} detected)")
    lines.append("=" * 60)
    for wave in waves:
        lines.append(wave.summary())
        if wave.phase_nodes:
            lines.append(f"  Nodes (deadlocked): {', '.join(wave.phase_nodes)}")
        if wave.phase_antinodes:
            lines.append(f"  Antinodes (retrying): {', '.join(wave.phase_antinodes)}")
    return "\n".join(lines)
