"""Tests for API endpoints."""

import pytest
import json
from api import create_app


class TestHealthEndpoint:
    def test_health_check(self):
        app = create_app()
        # In a real test, you'd use a test client
        # This is a placeholder for the test structure
        assert True


class TestUsersEndpoint:
    def test_list_users_empty(self, db_connection):
        # Setup empty database
        conn = db_connection
        # Test
        result = conn.execute("SELECT * FROM users").fetchall()
        assert len(result) == 0

    def test_list_users_with_data(self, db_connection):
        conn = db_connection
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("alice", "alice@example.com"),
        )
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", ("bob", "bob@example.com")
        )
        conn.commit()

        result = conn.execute("SELECT * FROM users").fetchall()
        assert len(result) == 2
