"""Tests for lockfile parsing."""
import json
import os
import tempfile
import pytest
from ussy_stratax.scanner.lockfile import Dependency, LockfileParser


class TestDependency:
    def test_create(self):
        d = Dependency("numpy", "1.24.0", "pip")
        assert d.name == "numpy"
        assert d.version == "1.24.0"
        assert d.source == "pip"

    def test_repr(self):
        d = Dependency("numpy", "1.24.0", "pip")
        assert "numpy" in repr(d)
        assert "1.24.0" in repr(d)

    def test_equality(self):
        d1 = Dependency("numpy", "1.24.0", "pip")
        d2 = Dependency("numpy", "1.24.0", "pip")
        assert d1 == d2

    def test_inequality(self):
        d1 = Dependency("numpy", "1.24.0", "pip")
        d2 = Dependency("numpy", "1.25.0", "pip")
        assert d1 != d2

    def test_hash(self):
        d1 = Dependency("numpy", "1.24.0", "pip")
        d2 = Dependency("numpy", "1.24.0", "pip")
        assert hash(d1) == hash(d2)
        assert len({d1, d2}) == 1


class TestLockfileParser:
    def setup_method(self):
        self.parser = LockfileParser()
        self.tmpdir = tempfile.mkdtemp()

    def _write_file(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_parse_requirements_txt(self):
        path = self._write_file("requirements.txt", """
# Comment line
numpy==1.24.0
requests>=2.28.0
flask~=2.3.0
""")
        deps = self.parser.parse(path)
        assert len(deps) == 3
        names = {d.name for d in deps}
        assert "numpy" in names
        assert "requests" in names
        assert "flask" in names
        assert deps[0].version == "1.24.0"
        assert deps[0].source == "pip"

    def test_parse_empty_requirements(self):
        path = self._write_file("requirements.txt", """
# Only comments

""")
        deps = self.parser.parse(path)
        assert len(deps) == 0

    def test_parse_npm_lockfile_v2(self):
        data = {
            "name": "test-project",
            "lockfileVersion": 2,
            "packages": {
                "": {},
                "node_modules/lodash": {"version": "4.17.21"},
                "node_modules/express": {"version": "4.18.2"},
            },
        }
        path = self._write_file("package-lock.json", json.dumps(data))
        deps = self.parser.parse(path)
        assert len(deps) == 2
        names = {d.name for d in deps}
        assert "lodash" in names
        assert "express" in names
        assert deps[0].source == "npm"

    def test_parse_npm_lockfile_v1(self):
        data = {
            "dependencies": {
                "lodash": {"version": "4.17.21"},
                "express": {"version": "4.18.2"},
            }
        }
        path = self._write_file("package-lock.json", json.dumps(data))
        deps = self.parser.parse(path)
        assert len(deps) == 2

    def test_parse_pipfile_lock(self):
        data = {
            "default": {
                "numpy": {"version": "==1.24.0"},
                "requests": {"version": "==2.28.0"},
            },
            "develop": {
                "pytest": {"version": "==7.0.0"},
            },
        }
        path = self._write_file("Pipfile.lock", json.dumps(data))
        deps = self.parser.parse(path)
        assert len(deps) == 3
        versions = {d.name: d.version for d in deps}
        assert versions["numpy"] == "1.24.0"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.parser.parse("/nonexistent/file.txt")

    def test_requirements_with_comments_and_flags(self):
        path = self._write_file("requirements.txt", """
# Dev dependencies
pytest==7.0.0
--index-url https://pypi.org/simple
coverage>=6.0
-r other-requirements.txt
""")
        deps = self.parser.parse(path)
        assert len(deps) == 2  # Only pytest and coverage

    def test_auto_detect_json(self):
        data = {"packages": {"node_modules/lodash": {"version": "4.17.21"}}}
        path = self._write_file("unknown.lock", json.dumps(data))
        deps = self.parser.parse(path)
        assert len(deps) == 1

    def test_auto_detect_txt(self):
        path = self._write_file("unknown.lock", "numpy==1.24.0\n")
        deps = self.parser.parse(path)
        assert len(deps) == 1
