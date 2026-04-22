"""Tests for ussy_sqlite."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from ussy_sqlite import ConnectionPool, JsonAdapter, MigrationManager, QueryBuilder


class TestJsonAdapter:
    def test_roundtrip(self) -> None:
        data = {"a": [1, 2, 3], "b": "hello"}
        encoded = JsonAdapter.encode(data)
        decoded = JsonAdapter.decode(encoded)
        assert decoded == data


class TestConnectionPool:
    def test_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            pool = ConnectionPool(db, max_size=2)
            with pool.checkout() as conn:
                conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO t VALUES (1)")
            with pool.checkout() as conn:
                row = conn.execute("SELECT * FROM t").fetchone()
                assert row["id"] == 1
            pool.close()

    def test_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            pool = ConnectionPool(db, max_size=1)
            with pool.checkout():
                with pytest.raises(RuntimeError):
                    with pool.checkout():
                        pass
            pool.close()


class TestMigrationManager:
    def test_migration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            pool = ConnectionPool(db)
            mgr = MigrationManager(pool)
            assert mgr.current_version() == 0
            mgr.apply(1, "create_users", "CREATE TABLE users (id INTEGER PRIMARY KEY)")
            assert mgr.current_version() == 1
            mgr.apply(1, "create_users", "CREATE TABLE users (id INTEGER PRIMARY KEY)")
            assert mgr.current_version() == 1
            pool.close()

    def test_migrate_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            pool = ConnectionPool(db)
            mgr = MigrationManager(pool)
            migrations = [
                (1, "create_a", "CREATE TABLE a (id INTEGER PRIMARY KEY)"),
                (2, "create_b", "CREATE TABLE b (name TEXT)"),
            ]
            mgr.migrate(migrations)
            assert mgr.current_version() == 2
            pool.close()


class TestQueryBuilder:
    def test_select(self) -> None:
        qb = QueryBuilder("items")
        sql, params = qb.select(
            columns=["id", "name"], where={"status": "ok"}, order_by="id", limit=10
        )
        assert "SELECT id, name FROM items" in sql
        assert "status = ?" in sql
        assert "ORDER BY id" in sql
        assert "LIMIT 10" in sql
        assert params == ("ok",)

    def test_insert(self) -> None:
        qb = QueryBuilder("items")
        sql, params = qb.insert({"id": 1, "name": "foo"})
        assert "INSERT INTO items" in sql
        assert params == (1, "foo")

    def test_upsert(self) -> None:
        qb = QueryBuilder("items")
        sql, params = qb.upsert({"id": 1, "name": "foo"}, key="id")
        assert "ON CONFLICT" in sql
        assert params == (1, "foo")
