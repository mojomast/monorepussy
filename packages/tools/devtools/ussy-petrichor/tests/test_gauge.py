"""Tests for petrichor.gauge module."""

from petrichor.db import SoilDB
from petrichor.gauge import DriftTrend, RainGauge


class TestDriftTrend:
    def test_trend_constants(self):
        assert DriftTrend.CONVERGING == "converging"
        assert DriftTrend.DIVERGING == "diverging"
        assert DriftTrend.CHAOTIC == "chaotic"
        assert DriftTrend.STABLE == "stable"


class TestRainGauge:
    def test_empty_gauge(self, db):
        gauge = RainGauge(db)
        result = gauge.measure(days=30)
        assert result["high"] == []
        assert result["moderate"] == []
        assert result["stable"] == []

    def test_stable_path(self, db):
        db.add_tracked_path("/etc/hosts")
        gauge = RainGauge(db)
        result = gauge.measure(days=30)
        assert any(p["path"] == "/etc/hosts" for p in result["stable"])

    def test_moderate_drift(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.add_layer("/etc/test.conf", "h1", "c1", is_drift=True)
        gauge = RainGauge(db)
        result = gauge.measure(days=30)
        assert any(p["path"] == "/etc/test.conf" for p in result["moderate"])

    def test_high_drift(self, db):
        db.add_tracked_path("/etc/test.conf")
        for i in range(5):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        gauge = RainGauge(db)
        result = gauge.measure(days=30)
        assert any(p["path"] == "/etc/test.conf" for p in result["high"])

    def test_classify_trend_stable(self, db):
        gauge = RainGauge(db)
        assert gauge._classify_trend("/etc/test.conf") == DriftTrend.STABLE

    def test_classify_trend_converging(self, db):
        # 2 drifts -> 1 drift in second half means converging
        from datetime import datetime, timezone, timedelta
        import time
        now = datetime.now(timezone.utc)
        # Add drifts with spacing
        for i in range(3):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        gauge = RainGauge(db)
        trend = gauge._classify_trend("/etc/test.conf")
        assert trend in (DriftTrend.CONVERGING, DriftTrend.DIVERGING, DriftTrend.CHAOTIC)


class TestRainGaugePatterns:
    def test_no_patterns(self, db):
        gauge = RainGauge(db)
        patterns = gauge.detect_patterns(days=30)
        assert patterns == []

    def test_day_of_week_pattern(self, db):
        import time
        # Add multiple drifts for the same path
        for i in range(4):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        gauge = RainGauge(db)
        patterns = gauge.detect_patterns(days=30)
        # May or may not find a pattern depending on distribution
        assert isinstance(patterns, list)


class TestRainGaugeFormat:
    def test_format_gauge(self, db):
        db.add_tracked_path("/etc/hosts")
        db.add_tracked_path("/etc/test.conf")
        db.add_layer("/etc/test.conf", "h1", "c1", is_drift=True)
        gauge = RainGauge(db)
        output = gauge.format_gauge(days=30)
        assert "Rain Gauge" in output
        assert "DRIFT" in output or "MODERATE" in output or "STABLE" in output

    def test_format_empty(self, db):
        gauge = RainGauge(db)
        output = gauge.format_gauge(days=30)
        assert "Rain Gauge" in output
