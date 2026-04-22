"""Main application entry point."""

import sys
from typing import Optional, Dict, List
from auth import authenticate_user, check_permissions
from utils import format_response, validate_input
from models import User, Project, Task
from database import get_connection, execute_query
from cache import get_cache, set_cache
from notifications import send_email, send_slack


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the application."""
    argv = argv or sys.argv[1:]

    if not argv:
        print("Usage: app <command> [options]")
        return 1

    command = argv[0]

    if command == "serve":
        return serve_application(argv[1:])
    elif command == "migrate":
        return run_migrations(argv[1:])
    elif command == "seed":
        return seed_database(argv[1:])
    else:
        print(f"Unknown command: {command}")
        return 1


def serve_application(args: List[str]) -> int:
    """Start the web server."""
    from api import create_app

    app = create_app()
    app.run(host="0.0.0.0", port=8080)
    return 0


def run_migrations(args: List[str]) -> int:
    """Run database migrations."""
    conn = get_connection()
    try:
        execute_query(conn, "BEGIN TRANSACTION")
        # Migration logic here
        execute_query(conn, "COMMIT")
    except Exception as e:
        execute_query(conn, "ROLLBACK")
        print(f"Migration failed: {e}")
        return 1
    finally:
        conn.close()
    return 0


def seed_database(args: List[str]) -> int:
    """Seed the database with initial data."""
    users = [
        User(id=1, name="admin", email="admin@example.com"),
        User(id=2, name="user", email="user@example.com"),
    ]

    for user in users:
        cache_key = f"user:{user.id}"
        set_cache(cache_key, user.to_dict())

    return 0


if __name__ == "__main__":
    sys.exit(main())
