"""Tests for tarot.community module."""

import pytest

from tarot.community import CommunityDatabase, COMMUNITY_SEED_DATA


class TestCommunityDatabase:
    def test_in_memory_creation(self):
        db = CommunityDatabase()
        assert db.get_total_decision_types() > 0

    def test_seed_data_loaded(self):
        db = CommunityDatabase()
        # Should have seeded data
        types = db.get_decision_types()
        assert len(types) > 0
        assert "Microservices migration" in types

    def test_get_outcomes_for_decision(self):
        db = CommunityDatabase()
        outcomes = db.get_outcomes_for_decision("Microservices migration")
        assert len(outcomes) >= 2
        outcome_names = [o["outcome"] for o in outcomes]
        assert "Distributed monolith" in outcome_names

    def test_search_outcomes(self):
        db = CommunityDatabase()
        results = db.search_outcomes("Redis")
        assert len(results) >= 1

    def test_search_no_results(self):
        db = CommunityDatabase()
        results = db.search_outcomes("nonexistent_technology_xyz")
        assert len(results) == 0

    def test_submit_outcome(self):
        db = CommunityDatabase()
        db.submit_outcome("Custom decision", "Custom outcome")
        # Should be in submitted_outcomes table
        cursor = db.conn.execute("SELECT COUNT(*) FROM submitted_outcomes")
        assert cursor.fetchone()[0] == 1

    def test_get_decision_types(self):
        db = CommunityDatabase()
        types = db.get_decision_types()
        assert isinstance(types, list)
        assert len(types) > 5

    def test_get_outcome_counts(self):
        db = CommunityDatabase()
        counts = db.get_outcome_counts()
        assert isinstance(counts, dict)
        assert len(counts) > 0

    def test_get_total_organizations(self):
        db = CommunityDatabase()
        total = db.get_total_organizations()
        assert total > 0

    def test_context_manager(self):
        with CommunityDatabase() as db:
            assert db.get_total_decision_types() > 0

    def test_persistence(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db1 = CommunityDatabase(db_path)
            db1.submit_outcome("Test", "Good outcome")
            db1.close()

            db2 = CommunityDatabase(db_path)
            # Seeded data should still be there
            assert db2.get_total_decision_types() > 0
            # Submitted outcome should be there
            cursor = db2.conn.execute("SELECT COUNT(*) FROM submitted_outcomes")
            assert cursor.fetchone()[0] == 1
            db2.close()
        finally:
            import os
            os.unlink(db_path)

    def test_probability_calculation(self):
        db = CommunityDatabase()
        outcomes = db.get_outcomes_for_decision("Single AZ deployment")
        # Single AZ: 27/30 had availability outage
        for o in outcomes:
            if o["outcome"] == "Availability outage":
                assert o["probability"] == pytest.approx(0.9, abs=0.01)
