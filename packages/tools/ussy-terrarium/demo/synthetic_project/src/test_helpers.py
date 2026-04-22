"""Testing utilities and fixtures."""

import pytest
from typing import Generator
from database import get_connection, init_database


@pytest.fixture
def db_connection():
    """Provide a database connection for tests."""
    init_database()
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    from models import User

    return User(id=1, name="test_user", email="test@example.com")


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    from models import Project

    return Project(id=1, name="Test Project", description="A test project", owner_id=1)


class TestHelpers:
    """Helper methods for tests."""

    @staticmethod
    def assert_response_ok(response):
        """Assert that a response is OK."""
        assert response.status_code == 200

    @staticmethod
    def assert_json_response(response):
        """Assert that a response is JSON."""
        assert "application/json" in response.content_type

    @staticmethod
    def create_test_user(conn, name: str = "test", email: str = "test@test.com"):
        """Create a test user in the database."""
        cursor = conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
        )
        conn.commit()
        return cursor.lastrowid
