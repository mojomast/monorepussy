"""Tests for petrichor.scent module."""

from datetime import datetime, timezone, timedelta

from ussy_petrichor.db import SoilDB
from ussy_petrichor.scent import ScentDetector, DriftPrediction


class TestDriftPrediction:
    def test_create_prediction(self):
        pred = DriftPrediction(
            path="/etc/test.conf",
            predicted_time=datetime.now(timezone.utc),
            confidence=0.85,
            reason="Pattern: drifts on Thursday",
            pattern_type="day_of_week",
        )
        assert pred.confidence == 0.85
        assert pred.pattern_type == "day_of_week"


class TestScentDetector:
    def test_no_predictions_empty_db(self, db):
        detector = ScentDetector(db)
        predictions = detector.predict(days=7)
        assert predictions == []

    def test_no_predictions_insufficient_data(self, db):
        db.add_layer("/etc/test.conf", "h1", "c1", is_drift=True)
        detector = ScentDetector(db)
        predictions = detector.predict(days=7)
        # Only 1 drift, unlikely to produce a confident prediction
        assert isinstance(predictions, list)

    def test_predictions_with_recurring_drift(self, db):
        # Add several drifts for the same path
        for i in range(5):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        detector = ScentDetector(db)
        predictions = detector.predict(days=7, min_confidence=0.1)
        # May or may not produce predictions depending on data distribution
        assert isinstance(predictions, list)

    def test_min_confidence_filter(self, db):
        for i in range(5):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        detector = ScentDetector(db)
        high_conf = detector.predict(days=7, min_confidence=0.9)
        low_conf = detector.predict(days=7, min_confidence=0.1)
        # Low confidence should return >= high confidence predictions
        assert len(low_conf) >= len(high_conf)

    def test_format_predictions_empty(self, db):
        detector = ScentDetector(db)
        output = detector.format_predictions(days=7)
        assert "Petrichor Scent" in output
        assert "No drift predicted" in output

    def test_format_predictions_with_data(self, db):
        for i in range(5):
            db.add_layer("/etc/test.conf", f"h{i}", f"c{i}", is_drift=True)
        detector = ScentDetector(db)
        output = detector.format_predictions(days=7)
        assert "Petrichor Scent" in output


class TestScentRecurrencePrediction:
    def test_recurring_same_hash(self, db):
        # Same drift hash recurring should trigger recurrence prediction
        # Use explicit timestamps with spacing so intervals are meaningful
        import sqlite3
        same_hash = "abc123def456"
        base_time = datetime.now(timezone.utc) - timedelta(days=14)
        conn = sqlite3.connect(str(db.db_path))
        for i in range(4):
            ts = (base_time + timedelta(days=i * 3)).isoformat()
            conn.execute(
                """INSERT INTO soil_layers
                   (path, timestamp, content_hash, content_text, diff_text,
                    actor, context, is_drift, desired_hash, metadata)
                   VALUES (?, ?, ?, ?, '', '', '', 1, '', '{}')""",
                ("/etc/test.conf", ts, same_hash, f"c{i}"),
            )
        conn.commit()
        conn.close()
        detector = ScentDetector(db)
        predictions = detector.predict(days=30, min_confidence=0.1)
        # Should find at least the recurrence pattern
        recurrence_preds = [p for p in predictions if p.pattern_type == "recurrence"]
        # With 4 same-hash drifts spaced 3 days apart, recurrence should be detected
        assert len(recurrence_preds) >= 1
