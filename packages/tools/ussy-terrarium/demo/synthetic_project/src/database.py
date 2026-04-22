"""Database connection and query utilities."""

import sqlite3
from typing import Optional
from contextlib import contextmanager

DB_PATH = "app.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction():
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(conn, query: str, params: tuple = ()):
    """Execute a query and return results."""
    cursor = conn.execute(query, params)
    return cursor


def init_database():
    """Initialize the database schema."""
    with transaction() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                salt TEXT,
                auth_token TEXT,
                token_expires REAL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER REFERENCES users(id),
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                project_id INTEGER REFERENCES projects(id),
                assignee_id INTEGER REFERENCES users(id),
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                UNIQUE(user_id, resource, action)
            )
        """)
