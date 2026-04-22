"""Tests for authentication module."""

import pytest
from auth import authenticate_user, hash_password, verify_password, check_permissions
from models import User


class TestAuthenticateUser:
    def test_valid_credentials(self, db_connection):
        # Setup
        conn = db_connection
        password_hash, salt = hash_password("secret123")
        conn.execute(
            "INSERT INTO users (name, email, password_hash, salt) VALUES (?, ?, ?, ?)",
            ("alice", "alice@example.com", password_hash, salt),
        )
        conn.commit()

        # Test
        user = authenticate_user("alice", "secret123")
        assert user is not None
        assert user.name == "alice"

    def test_invalid_password(self, db_connection):
        conn = db_connection
        password_hash, salt = hash_password("secret123")
        conn.execute(
            "INSERT INTO users (name, email, password_hash, salt) VALUES (?, ?, ?, ?)",
            ("bob", "bob@example.com", password_hash, salt),
        )
        conn.commit()

        user = authenticate_user("bob", "wrongpassword")
        assert user is None

    def test_user_not_found(self):
        user = authenticate_user("nonexistent", "password")
        assert user is None


class TestPasswordHashing:
    def test_hash_password(self):
        password_hash, salt = hash_password("mypassword")
        assert password_hash is not None
        assert salt is not None
        assert len(salt) == 32  # 16 bytes hex

    def test_verify_password(self):
        password_hash, salt = hash_password("mypassword")
        assert verify_password("mypassword", password_hash, salt) is True
        assert verify_password("wrongpassword", password_hash, salt) is False

    def test_different_salts_produce_different_hashes(self):
        hash1, salt1 = hash_password("samepassword")
        hash2, salt2 = hash_password("samepassword")
        assert hash1 != hash2


class TestCheckPermissions:
    def test_has_permission(self, db_connection):
        conn = db_connection
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("admin", "admin@example.com"),
        )
        conn.execute(
            "INSERT INTO permissions (user_id, resource, action) VALUES (?, ?, ?)",
            (1, "projects", "create"),
        )
        conn.commit()

        user = User(id=1, name="admin", email="admin@example.com")
        assert check_permissions(user, "projects", "create") is True

    def test_no_permission(self, db_connection):
        user = User(id=2, name="user", email="user@example.com")
        assert check_permissions(user, "projects", "delete") is False
