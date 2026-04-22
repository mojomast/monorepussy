"""Environment variable capture and restore."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import EnvironmentState

# Patterns that indicate secret/sensitive values (should be excluded by default)
SECRET_PATTERNS = {
    "KEY", "SECRET", "PASSWORD", "TOKEN", "AUTH", "CREDENTIAL",
    "PRIVATE", "CERT", "SIGNATURE", "API_KEY", "ACCESS_KEY",
}

# Environment variables that are always relevant for development
RELEVANT_PREFIXES = {
    "PATH", "PYTHON", "GOPATH", "GOROOT", "NODE", "NPM",
    "JAVA_", "RUST", "CARGO", "RUBY", "GEM", "RAILS",
    "DOCKER", "KUBERNETES", "AWS_", "GCP_", "HOME", "USER",
    "LANG", "LC_", "EDITOR", "VISUAL", "SHELL", "TERM",
    "VIRTUAL_ENV", "CONDA_", "PIP_", "VENV",
    "DATABASE_", "DB_", "REDIS_", "MONGO_",
    "PORT", "HOST", "DEBUG", "ENV", "LOG_LEVEL",
    "PROJECT", "APP_", "SERVICE",
}


def capture_environment(
    project_dir: str = "",
    include_secrets: bool = False,
) -> EnvironmentState:
    """Capture project-relevant environment variables.
    
    Args:
        project_dir: Project directory to scan for .env files.
        include_secrets: If True, include variables matching secret patterns.
    """
    variables = {}
    path_entries = []
    python_path_entries = []
    env_files = []

    for key, value in os.environ.items():
        # Filter secrets unless explicitly included
        if not include_secrets and _is_secret(key):
            continue
        # Skip very long values
        if len(value) > 1000:
            continue
        variables[key] = value

    # Parse PATH
    path_str = os.environ.get("PATH", "")
    if path_str:
        path_entries = path_str.split(os.pathsep)

    # Parse PYTHONPATH
    pypath_str = os.environ.get("PYTHONPATH", "")
    if pypath_str:
        python_path_entries = pypath_str.split(os.pathsep)

    # Scan for .env files in project directory
    if project_dir:
        env_files = _find_env_files(project_dir)

    return EnvironmentState(
        variables=variables,
        path_entries=path_entries,
        python_path_entries=python_path_entries,
        env_files=env_files,
    )


def _is_secret(key: str) -> bool:
    """Check if an environment variable key looks like a secret."""
    key_upper = key.upper()
    return any(pattern in key_upper for pattern in SECRET_PATTERNS)


def _is_relevant(key: str) -> bool:
    """Check if an environment variable is relevant for development."""
    key_upper = key.upper()
    return any(key_upper.startswith(prefix) or key_upper == prefix for prefix in RELEVANT_PREFIXES)


def _find_env_files(project_dir: str) -> List[str]:
    """Find .env files in the project directory."""
    env_files = []
    project_path = Path(project_dir)
    
    if not project_path.exists():
        return env_files

    # Look for common .env file patterns
    env_patterns = [".env", ".env.local", ".env.development", ".env.production", ".env.test"]
    for pattern in env_patterns:
        env_path = project_path / pattern
        if env_path.exists() and env_path.is_file():
            env_files.append(str(env_path))

    return env_files


def parse_env_file(path: str, include_secrets: bool = False) -> Dict[str, str]:
    """Parse a .env file and return key-value pairs.
    
    Args:
        path: Path to the .env file.
        include_secrets: If True, include variables matching secret patterns.
    """
    result = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2).strip().strip('"').strip("'")
                    if not include_secrets and _is_secret(key):
                        continue
                    result[key] = value
    except OSError:
        pass
    return result


def restore_environment(state: EnvironmentState, dry_run: bool = False) -> bool:
    """Restore environment variables (sets them in the current process).
    
    Note: This only affects the current process and its children.
    It cannot modify the parent shell's environment directly.
    """
    if dry_run:
        return True

    for key, value in state.variables.items():
        os.environ[key] = value
    return True


def generate_env_export_script(state: EnvironmentState) -> str:
    """Generate a shell script that exports the environment variables.
    
    This can be sourced to restore the environment in the user's shell.
    """
    lines = ["#!/bin/bash", "# Snapshot environment restore script", ""]
    for key, value in sorted(state.variables.items()):
        # Escape single quotes in value
        escaped = value.replace("'", "'\\''")
        lines.append(f"export {key}='{escaped}'")
    lines.append("")
    return "\n".join(lines)
