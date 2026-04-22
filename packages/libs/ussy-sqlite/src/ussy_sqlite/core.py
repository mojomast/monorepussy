"""Core utilities for SQLite utilities and schema migration."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Sequence


class JsonAdapter:
    """Serialize/deserialize Python objects to/from SQLite TEXT columns."""

    @staticmethod
    def encode(obj: Any) -> str:
        """Encode *obj* as a JSON string."""
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def decode(text: str) -> Any:
        """Decode a JSON string back to a Python object."""
        return json.loads(text)

    @classmethod
    def register(cls, conn: sqlite3.Connection) -> None:
        """Register JSON adapters on *conn* for ``dict`` and ``list``."""
        sqlite3.register_adapter(dict, lambda d: cls.encode(d))
        sqlite3.register_adapter(list, lambda L: cls.encode(L))
        sqlite3.register_converter("JSON", lambda b: cls.decode(b.decode("utf-8")))


class ConnectionPool:
    """Simple SQLite connection pool with context-manager checkout."""

    def __init__(
        self, db_path: Path | str, max_size: int = 5, timeout: float = 5.0
    ) -> None:
        """Initialize pool.

        Args:
            db_path: Path to the SQLite database file.
            max_size: Maximum number of connections to keep open.
            timeout: Seconds to wait for an available connection.
        """
        self._db_path = str(db_path)
        self._max_size = max_size
        self._timeout = timeout
        self._pool: list[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._checked_out = 0

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._db_path,
            timeout=self._timeout,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        JsonAdapter.register(conn)
        return conn

    @contextmanager
    def checkout(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection from the pool, returning it on exit."""
        conn: sqlite3.Connection | None = None
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            elif self._checked_out < self._max_size:
                conn = self._create_connection()
            self._checked_out += 1

        if conn is None:
            raise RuntimeError("Connection pool exhausted")

        try:
            yield conn
        finally:
            with self._lock:
                self._checked_out -= 1
                if len(self._pool) < self._max_size:
                    self._pool.append(conn)
                else:
                    conn.close()

    def close(self) -> None:
        """Close all pooled connections."""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()

    def execute(
        self, sql: str, parameters: Sequence[Any] | None = None
    ) -> sqlite3.Cursor:
        """Execute a query using a checked-out connection."""
        with self.checkout() as conn:
            return conn.execute(sql, parameters or ())


class MigrationManager:
    """Track and apply schema migrations using a simple version table."""

    _TABLE_SQL: str = (
        "CREATE TABLE IF NOT EXISTS __migrations__ ("
        "    version INTEGER PRIMARY KEY,"
        "    name TEXT NOT NULL,"
        "    applied_at TEXT DEFAULT (datetime('now'))"
        ")"
    )

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._pool.checkout() as conn:
            conn.execute(self._TABLE_SQL)

    def current_version(self) -> int:
        """Return the highest applied migration version, or ``0`` if none."""
        with self._pool.checkout() as conn:
            row = conn.execute("SELECT MAX(version) FROM __migrations__").fetchone()
            return row[0] or 0

    def apply(self, version: int, name: str, sql: str) -> None:
        """Apply a single migration if it has not already been applied.

        Args:
            version: Monotonically increasing migration number.
            name: Human-readable migration name.
            sql: SQL statements to execute (may contain multiple statements).
        """
        with self._pool.checkout() as conn:
            existing = conn.execute(
                "SELECT 1 FROM __migrations__ WHERE version = ?", (version,)
            ).fetchone()
            if existing:
                return

            conn.executescript(sql)
            conn.execute(
                "INSERT INTO __migrations__ (version, name) VALUES (?, ?)",
                (version, name),
            )

    def migrate(self, migrations: Sequence[tuple[int, str, str]]) -> None:
        """Apply a sequence of migrations in order.

        Args:
            migrations: Sequence of ``(version, name, sql)`` tuples.
        """
        for version, name, sql in sorted(migrations, key=lambda m: m[0]):
            self.apply(version, name, sql)


@dataclass(frozen=True, slots=True)
class QueryBuilder:
    """Lightweight query builder for common SELECT/INSERT patterns."""

    table: str

    def select(
        self,
        columns: Sequence[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> tuple[str, tuple[Any, ...]]:
        """Build a SELECT query and return ``(sql, params)``.

        Args:
            columns: Columns to select (default ``*``).
            where: Equality conditions ``col = val``.
            order_by: ``ORDER BY`` clause.
            limit: ``LIMIT`` value.
        """
        cols = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols} FROM {self.table}"
        params: list[Any] = []

        if where:
            conditions = []
            for col, val in where.items():
                conditions.append(f"{col} = ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(conditions)

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += f" LIMIT {limit}"

        return sql, tuple(params)

    def insert(self, data: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
        """Build an INSERT query and return ``(sql, params)``.

        Args:
            data: Column-value mapping.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})"
        return sql, tuple(data.values())

    def upsert(self, data: dict[str, Any], key: str) -> tuple[str, tuple[Any, ...]]:
        """Build an INSERT ... ON CONFLICT UPDATE query.

        Args:
            data: Column-value mapping.
            key: Conflict target column (must have a UNIQUE constraint).
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{col} = excluded.{col}" for col in data if col != key)
        sql = (
            f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT ({key}) DO UPDATE SET {updates}"
        )
        return sql, tuple(data.values())
