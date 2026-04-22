"""Tests for the project scanner."""
import json
import pytest
import tempfile
from pathlib import Path

from portmore.scanner import (
    detect_license_from_text,
    find_license_files,
    read_package_json,
    scan_project,
)


class TestDetectLicenseFromText:
    """Tests for license detection from text content."""

    def test_mit_license(self):
        text = "MIT License\n\nCopyright (c) 2024\n\nPermission is hereby granted..."
        assert detect_license_from_text(text) == "MIT"

    def test_apache_license(self):
        text = "Apache License\nVersion 2.0, January 2004\n..."
        assert detect_license_from_text(text) == "Apache-2.0"

    def test_gpl3_license(self):
        text = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n..."
        assert detect_license_from_text(text) == "GPL-3.0"

    def test_unknown_text(self):
        text = "Some random text that doesn't match any license"
        assert detect_license_from_text(text) is None

    def test_empty_text(self):
        assert detect_license_from_text("") is None

    def test_bsd3_license(self):
        text = "BSD 3-Clause License\n\nRedistribution and use in source and binary forms..."
        assert detect_license_from_text(text) == "BSD-3-Clause"

    def test_cc0_license(self):
        text = "Creative Commons Zero\nCC0\n..."
        assert detect_license_from_text(text) == "CC0-1.0"


class TestFindLicenseFiles:
    """Tests for finding license files in a directory."""

    def test_finds_license_file(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License")
        files = find_license_files(tmp_path)
        assert len(files) == 1

    def test_finds_license_md(self, tmp_path):
        (tmp_path / "LICENSE.md").write_text("MIT License")
        files = find_license_files(tmp_path)
        assert len(files) == 1

    def test_no_license_files(self, tmp_path):
        files = find_license_files(tmp_path)
        assert len(files) == 0

    def test_multiple_license_files(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License")
        (tmp_path / "LICENSE.md").write_text("MIT License")
        files = find_license_files(tmp_path)
        assert len(files) == 2


class TestReadPackageJson:
    """Tests for reading package.json."""

    def test_reads_valid_json(self, tmp_path):
        pkg = {"name": "test", "license": "MIT", "dependencies": {"express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = read_package_json(tmp_path)
        assert result is not None
        assert result["name"] == "test"
        assert result["license"] == "MIT"

    def test_no_package_json(self, tmp_path):
        result = read_package_json(tmp_path)
        assert result is None

    def test_invalid_json(self, tmp_path):
        (tmp_path / "package.json").write_text("not json{{{")
        result = read_package_json(tmp_path)
        assert result is None


class TestScanProject:
    """Tests for the full project scanner."""

    def test_nonexistent_path(self):
        info = scan_project("/nonexistent/path/xyz")
        assert info.name == "xyz"
        assert info.licenses == []

    def test_empty_directory(self, tmp_path):
        info = scan_project(str(tmp_path))
        assert info.name == tmp_path.name

    def test_with_license_file(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\n\nCopyright 2024")
        info = scan_project(str(tmp_path))
        assert "MIT" in info.licenses

    def test_with_package_json(self, tmp_path):
        pkg = {
            "name": "my-project",
            "license": "Apache-2.0",
            "dependencies": {"express": "^4.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        info = scan_project(str(tmp_path))
        assert "express" in info.dependencies
        assert "jest" in info.dev_dependencies

    def test_with_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        info = scan_project(str(tmp_path))
        assert len(info.modules) >= 2

    def test_ignores_venv(self, tmp_path):
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "site.py").write_text("# site")
        (tmp_path / "main.py").write_text("# main")
        info = scan_project(str(tmp_path))
        # Should not include .venv files
        venv_modules = [m for m in info.modules if ".venv" in m]
        assert len(venv_modules) == 0
