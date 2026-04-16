"""Pytest configuration and shared fixtures."""

import os
import tempfile
import shutil
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def temp_repo():
    """Create a temporary git repository with sample Python code."""
    tmpdir = tempfile.mkdtemp()
    
    # Initialize git repo
    os.system(f'cd {tmpdir} && git init && git config user.email "test@test.com" && git config user.name "Test"')

    # Create sample Python files
    os.makedirs(os.path.join(tmpdir, "src", "core"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "src", "utils"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "src", "auth"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "tests"), exist_ok=True)

    # Core module
    core_init = os.path.join(tmpdir, "src", "core", "__init__.py")
    with open(core_init, 'w') as f:
        f.write('"""Core module."""\n\ndef core_function():\n    pass\n\nclass CoreClass:\n    def public_method(self):\n        pass\n    def _private_method(self):\n        pass\n')

    # Utils module
    utils_init = os.path.join(tmpdir, "src", "utils", "__init__.py")
    with open(utils_init, 'w') as f:
        f.write('"""Utils module."""\n\nfrom src.core import core_function\n\ndef util_helper():\n    return core_function()\n\ndef _internal_helper():\n    pass\n')

    # Auth module
    auth_init = os.path.join(tmpdir, "src", "auth", "__init__.py")
    with open(auth_init, 'w') as f:
        f.write('"""Auth module."""\n\nfrom src.core import CoreClass\n\ndef authenticate():\n    obj = CoreClass()\n    return obj.public_method()\n\n# DEPRECATED: old_auth\nDEPRECATED_old_auth = True\n')

    # Test file
    test_file = os.path.join(tmpdir, "tests", "test_core.py")
    with open(test_file, 'w') as f:
        f.write('"""Tests."""\n\nfrom src.core import core_function, CoreClass\n\ndef test_core():\n    assert core_function() is None\n')

    # Main file
    main_file = os.path.join(tmpdir, "main.py")
    with open(main_file, 'w') as f:
        f.write('"""Main entry point."""\n\nfrom src.core import core_function\nfrom src.auth import authenticate\n\nif __name__ == "__main__":\n    authenticate()\n')

    # Commit everything
    os.system(f'cd {tmpdir} && git add -A && git commit -m "Initial commit"')

    # Make a second commit to add DEPRECATED marker
    with open(auth_init, 'a') as f:
        f.write('\n# DEPRECATED: use authenticate instead\nDEPRECATED_login = True\n')
    os.system(f'cd {tmpdir} && git add -A && git commit -m "Add deprecated markers"')

    # Create a merge commit (simulate a PR merge)
    os.system(f'cd {tmpdir} && git checkout -b feature-branch')
    feature_file = os.path.join(tmpdir, "src", "core", "feature.py")
    with open(feature_file, 'w') as f:
        f.write('"""New feature."""\n\nfrom src.utils import util_helper\n\ndef new_feature():\n    return util_helper()\n')
    os.system(f'cd {tmpdir} && git add -A && git commit -m "Add new feature"')
    os.system(f'cd {tmpdir} && git checkout main || git checkout master')
    os.system(f'cd {tmpdir} && git merge --no-ff feature-branch -m "Merge feature-branch"')

    yield tmpdir

    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_prs():
    """Create sample PullRequestInfo objects for testing."""
    from dosemate.git_parser import PullRequestInfo
    
    now = datetime.now()
    return [
        PullRequestInfo(
            id="pr_001",
            title="Add authentication",
            created_at=now - timedelta(days=3),
            merged_at=now - timedelta(days=2),
            files_changed=["src/auth/__init__.py", "src/core/__init__.py"],
            insertions=100,
            deletions=20,
            first_ci_at=now - timedelta(days=3, hours=1),
        ),
        PullRequestInfo(
            id="pr_002",
            title="Update utilities",
            created_at=now - timedelta(days=1, hours=12),
            merged_at=now - timedelta(days=1),
            files_changed=["src/utils/__init__.py"],
            insertions=50,
            deletions=10,
            first_ci_at=now - timedelta(days=1, hours=11),
        ),
        PullRequestInfo(
            id="pr_003",
            title="Auto-merge dependency update",
            created_at=now - timedelta(hours=2),
            merged_at=now - timedelta(hours=1, minutes=50),
            files_changed=["requirements.txt"],
            insertions=5,
            deletions=5,
            first_ci_at=now - timedelta(hours=2, minutes=5),
        ),
    ]


@pytest.fixture
def sample_commits():
    """Create sample CommitInfo objects for testing."""
    from dosemate.git_parser import CommitInfo
    
    now = datetime.now()
    return [
        CommitInfo(
            hash="abc1234",
            author="Alice",
            date=now - timedelta(days=5),
            message="Add auth module",
            files_changed=["src/auth/__init__.py"],
            insertions=80,
            deletions=5,
        ),
        CommitInfo(
            hash="def5678",
            author="Bob",
            date=now - timedelta(days=3),
            message="Fix auth bug",
            files_changed=["src/auth/__init__.py", "src/core/__init__.py"],
            insertions=15,
            deletions=30,
        ),
        CommitInfo(
            hash="ghi9012",
            author="Charlie",
            date=now - timedelta(days=1),
            message="Update docs",
            files_changed=["README.md"],
            insertions=10,
            deletions=2,
        ),
    ]
