"""Pytest configuration and shared fixtures."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ussy_petrichor.db import SoilDB


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def db(tmp_dir):
    """Create an initialized SoilDB in a temp directory."""
    soil_db = SoilDB(tmp_dir)
    soil_db.initialize()
    return soil_db


@pytest.fixture
def sample_config_text():
    """Sample nginx-like configuration text."""
    return """worker_connections=1024
worker_processes=auto
error_log=/var/log/nginx/error.log
pid=/run/nginx.pid
"""


@pytest.fixture
def sample_config_text_drifted():
    """Drifted version of the sample config."""
    return """worker_connections=2048
worker_processes=auto
error_log=/var/log/nginx/error.log
pid=/run/nginx.pid
"""


@pytest.fixture
def sample_config_text_v2():
    """Another variation of the config."""
    return """worker_connections=4096
worker_processes=4
error_log=/var/log/nginx/error.log
pid=/run/nginx.pid
"""


@pytest.fixture
def sample_file(tmp_dir, sample_config_text):
    """Create a sample config file."""
    path = os.path.join(tmp_dir, "nginx.conf")
    Path(path).write_text(sample_config_text)
    return path


@pytest.fixture
def desired_file(tmp_dir, sample_config_text):
    """Create a desired state file."""
    path = os.path.join(tmp_dir, "desired_nginx.conf")
    Path(path).write_text(sample_config_text)
    return path
