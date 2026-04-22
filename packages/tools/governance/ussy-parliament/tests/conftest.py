import os
import shutil
import tempfile
from pathlib import Path

import pytest

from parliament.session import ParliamentSession


collect_ignore = ["fixtures"]


@pytest.fixture
def tmp_chamber():
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def session(tmp_chamber):
    return ParliamentSession(tmp_chamber)


@pytest.fixture
def populated_session(session):
    session.register_agent("deploy-bot", "orchestration")
    session.register_agent("canary-bot", "validation")
    session.register_agent("security-scanner", "security")
    session.register_agent("cost-monitor", "finance")
    session.register_agent("rollback-bot", "operations")
    session.register_agent("test-runner", "quality")
    session.register_agent("compliance-audit", "governance")
    session.register_agent("on-call-human", "human")
    return session
