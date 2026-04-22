"""REST API handlers and route definitions."""

import json
from typing import Callable, Dict, List
from wsgiref.util import request_uri

from auth import AuthMiddleware, authenticate_user
from models import User, Project, Task
from database import get_connection, transaction
from utils import format_response, validate_input


class Router:
    """Simple URL router."""

    def __init__(self):
        self.routes: Dict[str, Callable] = {}

    def route(self, path: str):
        def decorator(func: Callable):
            self.routes[path] = func
            return func

        return decorator

    def dispatch(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        handler = self.routes.get(path, self.not_found)
        return handler(environ, start_response)

    def not_found(self, environ, start_response):
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Not found"}).encode()]


router = Router()


@router.route("/api/health")
def health_check(environ, start_response):
    """Health check endpoint."""
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(format_response({"status": "healthy"})).encode()]


@router.route("/api/users")
def list_users(environ, start_response):
    """List all users."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM users").fetchall()
        users = [User.from_row(row).to_dict() for row in rows]
        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps(format_response(users)).encode()]
    finally:
        conn.close()


@router.route("/api/projects")
def list_projects(environ, start_response):
    """List all projects."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM projects").fetchall()
        projects = [Project.from_row(row).to_dict() for row in rows]
        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps(format_response(projects)).encode()]
    finally:
        conn.close()


def create_app():
    """Create the WSGI application."""
    app = router.dispatch
    app = AuthMiddleware(app)
    return app
