"""Circadian state estimator — Bayesian-style estimation from time-of-day + session duration."""

from __future__ import annotations

import math
from datetime import datetime, timezone, time, timedelta
from typing import Optional

from ussy_circadia.zones import CognitiveZone, ZoneProbability


def _gaussian(x: float, mu: float, sigma: float) -> float:
    """Gaussian probability density (unnormalized)."""
    if sigma <= 0:
        return 0.0
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2)


class CircadianEstimator:
    """Estimates cognitive zone from time-of-day and session duration.

    Uses a simplified Bayesian model:
    - Prior: base circadian rates keyed to time-of-day
    - Likelihood: session duration modifier (longer sessions → more fatigue)
    - Posterior: zone probability distribution

    All times are in local hours (0-24) derived from UTC + configured offset.
    """

    # Circadian curve parameters: (peak_hour, sigma_hours)
    # Based on research: peak analytical ~10-12, creative ~16-18,
    # post-lunch dip ~14-16, circadian nadir ~2-4
    CIRCADIAN_PARAMS = {
        CognitiveZone.GREEN: [(10.0, 2.0), (9.0, 1.5)],      # Morning peak
        CognitiveZone.YELLOW: [(14.0, 1.5), (22.0, 2.0)],    # Post-lunch, late evening
        CognitiveZone.RED: [(3.0, 2.0), (15.0, 1.0)],        # Circadian nadir, afternoon dip
        CognitiveZone.CREATIVE: [(17.0, 2.0), (20.0, 2.5)],  # Evening creative window
    }

    # Session duration fatigue thresholds (hours)
    SESSION_FRESH_HOURS = 2.0
    SESSION_MODERATE_HOURS = 4.0
    SESSION_FATIGUE_HOURS = 6.0
    SESSION_EXTREME_HOURS = 8.0

    def __init__(self, utc_offset_hours: float = 0.0) -> None:
        """Initialize estimator with a UTC offset for local time.

        Args:
            utc_offset_hours: Hours offset from UTC (e.g., -5 for EST).
        """
        self.utc_offset_hours = utc_offset_hours

    def _local_hour(self, dt: Optional[datetime] = None) -> float:
        """Get current local hour (0-24) as a float.

        Args:
            dt: Optional datetime in UTC. If None, uses current UTC time.

        Returns:
            Local hour as a float (e.g., 14.5 for 2:30 PM).
        """
        if dt is None:
            dt = datetime.now(timezone.utc)
        local = dt + timedelta(hours=self.utc_offset_hours)
        return local.hour + local.minute / 60.0 + local.second / 3600.0

    def time_of_day_prior(self, local_hour: float) -> ZoneProbability:
        """Compute prior zone probabilities from time-of-day.

        Args:
            local_hour: Local hour as float (0-24).

        Returns:
            ZoneProbability prior distribution.
        """
        raw: dict[CognitiveZone, float] = {}
        for zone, params in self.CIRCADIAN_PARAMS.items():
            total = 0.0
            for mu, sigma in params:
                total += _gaussian(local_hour, mu, sigma)
            raw[zone] = total

        return ZoneProbability(
            green=raw.get(CognitiveZone.GREEN, 0.0),
            yellow=raw.get(CognitiveZone.YELLOW, 0.0),
            red=raw.get(CognitiveZone.RED, 0.0),
            creative=raw.get(CognitiveZone.CREATIVE, 0.0),
        )

    def session_duration_likelihood(
        self, session_hours: float
    ) -> ZoneProbability:
        """Compute likelihood of zones given session duration.

        Short sessions → green/creative likely.
        Long sessions → yellow/red likely.

        Args:
            session_hours: Duration of current coding session in hours.

        Returns:
            ZoneProbability likelihood distribution.
        """
        if session_hours < 0:
            session_hours = 0.0

        if session_hours <= self.SESSION_FRESH_HOURS:
            # Fresh: mostly green
            green = 0.6
            yellow = 0.2
            red = 0.05
            creative = 0.15
        elif session_hours <= self.SESSION_MODERATE_HOURS:
            # Moderate: shift toward yellow
            frac = (session_hours - self.SESSION_FRESH_HOURS) / (
                self.SESSION_MODERATE_HOURS - self.SESSION_FRESH_HOURS
            )
            green = 0.6 - 0.35 * frac
            yellow = 0.2 + 0.3 * frac
            red = 0.05 + 0.15 * frac
            creative = 0.15 - 0.1 * frac
        elif session_hours <= self.SESSION_FATIGUE_HOURS:
            # Fatigued: mostly yellow/red
            frac = (session_hours - self.SESSION_MODERATE_HOURS) / (
                self.SESSION_FATIGUE_HOURS - self.SESSION_MODERATE_HOURS
            )
            green = 0.25 - 0.15 * frac
            yellow = 0.5 - 0.1 * frac
            red = 0.2 + 0.25 * frac
            creative = 0.05
        else:
            # Extreme fatigue: mostly red
            extra = min(session_hours - self.SESSION_FATIGUE_HOURS, 4.0)
            frac = extra / 4.0
            green = 0.1 - 0.08 * frac
            yellow = 0.4 - 0.2 * frac
            red = 0.45 + 0.25 * frac
            creative = 0.05 - 0.03 * frac

        return ZoneProbability(
            green=max(green, 0.01),
            yellow=max(yellow, 0.01),
            red=max(red, 0.01),
            creative=max(creative, 0.01),
        )

    def estimate(
        self,
        dt: Optional[datetime] = None,
        session_hours: float = 0.0,
    ) -> ZoneProbability:
        """Estimate current cognitive zone using Bayesian combination.

        Combines time-of-day prior with session duration likelihood.

        Args:
            dt: Optional datetime in UTC. If None, uses current UTC time.
            session_hours: Duration of current coding session in hours.

        Returns:
            ZoneProbability posterior distribution.
        """
        local_hour = self._local_hour(dt)
        prior = self.time_of_day_prior(local_hour)
        likelihood = self.session_duration_likelihood(session_hours)

        # Bayesian update: posterior ∝ prior × likelihood
        posterior_green = prior.green * likelihood.green
        posterior_yellow = prior.yellow * likelihood.yellow
        posterior_red = prior.red * likelihood.red
        posterior_creative = prior.creative * likelihood.creative

        return ZoneProbability(
            green=posterior_green,
            yellow=posterior_yellow,
            red=posterior_red,
            creative=posterior_creative,
        )

    def current_zone(
        self,
        dt: Optional[datetime] = None,
        session_hours: float = 0.0,
    ) -> CognitiveZone:
        """Get the dominant cognitive zone.

        Args:
            dt: Optional datetime in UTC. If None, uses current UTC time.
            session_hours: Duration of current coding session in hours.

        Returns:
            The dominant CognitiveZone.
        """
        return self.estimate(dt, session_hours).dominant_zone
