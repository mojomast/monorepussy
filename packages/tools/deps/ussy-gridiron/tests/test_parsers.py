"""Tests for the dependency manifest parsers."""

import os
import pytest

from ussy_gridiron.parsers.package_json import parse_package_json
from ussy_gridiron.parsers.requirements_txt import parse_requirements_txt
from ussy_gridiron.parsers.pyproject_toml import parse_pyproject_toml


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestPackageJsonParser:
    """Tests for package.json parsing."""

    def test_parse_fixture(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, edges = parse_package_json(path)
        assert len(packages) > 0
        assert len(edges) > 0

    def test_project_name_extracted(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, edges = parse_package_json(path)
        assert "test-app" in packages

    def test_dependencies_parsed(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, edges = parse_package_json(path)
        dep_names = [e.target for e in edges]
        assert "express" in dep_names
        assert "lodash" in dep_names
        assert "axios" in dep_names

    def test_dev_dependencies_parsed(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, edges = parse_package_json(path)
        dev_edges = [e for e in edges if e.is_dev]
        dev_names = [e.target for e in dev_edges]
        assert "jest" in dev_names
        assert "eslint" in dev_names

    def test_version_rigidity_caret(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, _ = parse_package_json(path)
        # ^4.18.0 → rigidity 0.4
        assert packages["express"].version_rigidity == 0.4

    def test_edges_source_is_project(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        packages, edges = parse_package_json(path)
        for edge in edges:
            assert edge.source == "test-app"


class TestRequirementsTxtParser:
    """Tests for requirements.txt parsing."""

    def test_parse_fixture(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        packages, edges = parse_requirements_txt(path)
        assert len(packages) > 0
        assert len(edges) > 0

    def test_pinned_version(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        packages, _ = parse_requirements_txt(path)
        assert packages["flask"].version_rigidity == 1.0
        assert packages["flask"].version == "3.0.0"

    def test_ge_version(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        packages, _ = parse_requirements_txt(path)
        assert packages["requests"].version_rigidity == 0.2

    def test_compatible_release(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        packages, _ = parse_requirements_txt(path)
        assert packages["numpy"].version_rigidity == 0.6

    def test_bare_name(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        packages, _ = parse_requirements_txt(path)
        assert "click" in packages

    def test_comments_skipped(self):
        """Ensure comment lines are not parsed as packages."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# This is a comment\nflask==2.0.0\n")
            f.flush()
            packages, edges = parse_requirements_txt(f.name)
        os.unlink(f.name)
        assert "flask" in packages
        assert len(packages) == 2  # flask + root-project


class TestPyprojectTomlParser:
    """Tests for pyproject.toml parsing."""

    def test_parse_fixture(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        packages, edges = parse_pyproject_toml(path)
        assert len(packages) > 0
        assert len(edges) > 0

    def test_project_name_extracted(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        packages, _ = parse_pyproject_toml(path)
        assert "test-python-app" in packages

    def test_pep621_deps_parsed(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        packages, edges = parse_pyproject_toml(path)
        dep_names = [e.target for e in edges if not e.is_dev]
        assert "requests" in dep_names
        assert "pydantic" in dep_names

    def test_optional_deps_parsed(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        packages, edges = parse_pyproject_toml(path)
        dev_edges = [e for e in edges if e.is_dev]
        dev_names = [e.target for e in dev_edges]
        assert "pytest" in dev_names

    def test_version_extraction_ge(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        packages, _ = parse_pyproject_toml(path)
        # requests>=2.28.0 → version should be extracted
        assert packages["requests"].version == "2.28.0"
