"""Tests for circadia.estimator module."""

import pytest
from datetime import datetime, timezone, timedelta

from ussy_circadia.estimator import CircadianEstimator, _gaussian
from ussy_circadia.zones import CognitiveZone, ZoneProbability


class TestGaussian:
    """Tests for the Gaussian helper function."""

    def test_peak_at_mean(self):
        assert _gaussian(0.0, 0.0, 1.0) == 1.0

    def test_symmetric(self):
        assert abs(_gaussian(1.0, 0.0, 1.0) - _gaussian(-1.0, 0.0, 1.0)) < 1e-10

    def test_zero_sigma(self):
        assert _gaussian(0.0, 0.0, 0.0) == 0.0

    def test_decreases_away_from_mean(self):
        assert _gaussian(0.0, 0.0, 1.0) > _gaussian(1.0, 0.0, 1.0)

    def test_positive_value(self):
        assert _gaussian(5.0, 3.0, 2.0) > 0.0


class TestCircadianEstimator:
    """Tests for CircadianEstimator."""

    def test_init_default_offset(self):
        est = CircadianEstimator()
        assert est.utc_offset_hours == 0.0

    def test_init_custom_offset(self):
        est = CircadianEstimator(utc_offset_hours=-5.0)
        assert est.utc_offset_hours == -5.0

    def test_local_hour_utc(self):
        est = CircadianEstimator(utc_offset_hours=0.0)
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        hour = est._local_hour(dt)
        assert abs(hour - 10.5) < 0.01

    def test_local_hour_with_offset(self):
        est = CircadianEstimator(utc_offset_hours=-5.0)
        dt = datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc)
        hour = est._local_hour(dt)
        assert abs(hour - 10.0) < 0.01

    def test_time_of_day_prior_morning_peak(self):
        """10 AM should have high green probability."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        prior = est.time_of_day_prior(10.0)
        assert prior.green > prior.red

    def test_time_of_day_prior_nadir(self):
        """3 AM should have high red probability."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        prior = est.time_of_day_prior(3.0)
        assert prior.red > prior.green

    def test_time_of_day_prior_evening_creative(self):
        """6 PM should have relatively high creative probability."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        prior = est.time_of_day_prior(18.0)
        # Creative should be elevated at 18:00
        creative_18 = prior.creative
        prior_10 = est.time_of_day_prior(10.0)
        assert creative_18 > prior_10.creative

    def test_time_of_day_prior_afternoon_dip(self):
        """3 PM should have elevated yellow probability."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        prior = est.time_of_day_prior(15.0)
        assert prior.yellow > 0.05

    def test_session_duration_fresh(self):
        """Fresh session (<2h) should favor green."""
        est = CircadianEstimator()
        likelihood = est.session_duration_likelihood(1.0)
        assert likelihood.green > likelihood.red

    def test_session_duration_extreme(self):
        """Extreme session (>8h) should favor red."""
        est = CircadianEstimator()
        likelihood = est.session_duration_likelihood(10.0)
        assert likelihood.red > likelihood.green

    def test_session_duration_negative(self):
        """Negative session duration should be clamped to 0."""
        est = CircadianEstimator()
        likelihood = est.session_duration_likelihood(-1.0)
        assert likelihood.green > 0.0

    def test_session_duration_moderate(self):
        """Moderate session (3h) should shift toward yellow."""
        est = CircadianEstimator()
        like_0 = est.session_duration_likelihood(0.0)
        like_3 = est.session_duration_likelihood(3.0)
        assert like_3.yellow > like_0.yellow

    def test_estimate_combines_prior_and_likelihood(self):
        """Estimate should combine time-of-day and session duration."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        # 10 AM, fresh session → should be very green
        dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        prob = est.estimate(dt, session_hours=0.5)
        assert prob.dominant_zone == CognitiveZone.GREEN

    def test_estimate_3am_long_session(self):
        """3 AM with 8h session → should be very red."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        dt = datetime(2025, 1, 15, 3, 0, 0, tzinfo=timezone.utc)
        prob = est.estimate(dt, session_hours=8.0)
        assert prob.dominant_zone == CognitiveZone.RED

    def test_estimate_evening_creative(self):
        """6 PM, short session → should have creative potential."""
        est = CircadianEstimator(utc_offset_hours=0.0)
        dt = datetime(2025, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
        prob = est.estimate(dt, session_hours=0.5)
        # Creative should be relatively high
        assert prob.creative > prob.red

    def test_current_zone_returns_zone(self):
        est = CircadianEstimator(utc_offset_hours=0.0)
        dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        zone = est.current_zone(dt, session_hours=0.5)
        assert isinstance(zone, CognitiveZone)

    def test_probabilities_sum_to_one(self):
        est = CircadianEstimator(utc_offset_hours=0.0)
        dt = datetime(2025, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        prob = est.estimate(dt, session_hours=3.0)
        total = prob.green + prob.yellow + prob.red + prob.creative
        assert abs(total - 1.0) < 0.01

    def test_different_offsets_different_zones(self):
        """Different UTC offsets should produce different local hours."""
        est_east = CircadianEstimator(utc_offset_hours=-5.0)
        est_west = CircadianEstimator(utc_offset_hours=5.0)
        dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        hour_east = est_east._local_hour(dt)
        hour_west = est_west._local_hour(dt)
        assert hour_east != hour_west
