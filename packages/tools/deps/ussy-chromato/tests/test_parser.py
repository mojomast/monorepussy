"""Tests for chromato.parser — Dependency graph parser."""

import json
import os
import pytest
from pathlib import Path

from chromato.parser import (
    parse_dependency_file,
    _parse_requirements_txt,
    _parse_package_json,
    _parse_cargo_toml,
    _parse_go_mod,
    _parse_pom_xml,
    _parse_gemspec,
)


FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestRequirementsTxt:
    def test_parse_basic(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.28.0\nflask>=2.0\n")
        graph = _parse_requirements_txt(req)
        assert len(graph.dependencies) == 2
        assert graph.dependencies[0].name == "requests"
        assert graph.dependencies[0].version == "2.28.0"

    def test_parse_comments_and_blanks(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("# comment\n\nrequests==1.0\n\n")
        graph = _parse_requirements_txt(req)
        assert len(graph.dependencies) == 1

    def test_parse_version_ranges(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("django>=3.2,<5.0\n")
        graph = _parse_requirements_txt(req)
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].name == "django"
        assert graph.dependencies[0].version == "3.2"

    def test_parse_no_version(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests\n")
        graph = _parse_requirements_txt(req)
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].version == "0.0.0"

    def test_parse_fixture(self):
        graph = _parse_requirements_txt(FIXTURES / "requirements.txt")
        assert len(graph.dependencies) >= 8
        names = {d.name for d in graph.dependencies}
        assert "click" in names
        assert "requests" in names
        assert "django" in names

    def test_skip_flags(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("-r base.txt\nrequests==1.0\n")
        graph = _parse_requirements_txt(req)
        assert len(graph.dependencies) == 1


class TestPackageJson:
    def test_parse_basic(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "dependencies": {"express": "^4.18.0", "lodash": "^4.17.21"},
            "devDependencies": {"jest": "^29.0"},
        }))
        graph = _parse_package_json(pkg)
        assert len(graph.dependencies) == 3
        dep_names = {d.name for d in graph.dependencies}
        assert "express" in dep_names
        assert "lodash" in dep_names
        assert "jest" in dep_names
        # Check dev flag
        jest = next(d for d in graph.dependencies if d.name == "jest")
        assert jest.is_dev is True

    def test_parse_fixture(self):
        graph = _parse_package_json(FIXTURES / "package.json")
        assert len(graph.dependencies) >= 5
        names = {d.name for d in graph.dependencies}
        assert "express" in names
        assert "react" in names

    def test_parse_invalid_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text("not valid json {{{")
        graph = _parse_package_json(pkg)
        assert len(graph.dependencies) == 0

    def test_parse_empty_dependencies(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "test"}))
        graph = _parse_package_json(pkg)
        assert len(graph.dependencies) == 0


class TestCargoToml:
    def test_parse_basic(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text(
            '[package]\nname = "test"\n\n'
            '[dependencies]\nserde = "1.0"\ntokio = "1.28"\n\n'
            '[dev-dependencies]\ntokio-test = "0.4"\n'
        )
        graph = _parse_cargo_toml(cargo)
        assert len(graph.dependencies) == 3
        names = {d.name for d in graph.dependencies}
        assert "serde" in names
        assert "tokio" in names
        assert "tokio-test" in names

    def test_parse_table_form(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text(
            '[dependencies]\nclap = { version = "4.3", features = ["derive"] }\n'
        )
        graph = _parse_cargo_toml(cargo)
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].name == "clap"
        assert graph.dependencies[0].version == "4.3"

    def test_parse_fixture(self):
        graph = _parse_cargo_toml(FIXTURES / "Cargo.toml")
        assert len(graph.dependencies) >= 4
        names = {d.name for d in graph.dependencies}
        assert "serde" in names
        assert "tokio" in names


class TestGoMod:
    def test_parse_basic(self, tmp_path):
        gomod = tmp_path / "go.mod"
        gomod.write_text(
            "module example.com/test\n\ngo 1.21\n\n"
            "require (\n\tgithub.com/gin-gonic/gin v1.9.1\n)\n"
        )
        graph = _parse_go_mod(gomod)
        assert len(graph.dependencies) >= 1
        assert graph.dependencies[0].name == "gin"

    def test_parse_inline_require(self, tmp_path):
        gomod = tmp_path / "go.mod"
        gomod.write_text(
            "module example.com/test\n\ngo 1.21\n\n"
            "require github.com/google/uuid v1.3.0\n"
        )
        graph = _parse_go_mod(gomod)
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].name == "uuid"

    def test_parse_fixture(self):
        graph = _parse_go_mod(FIXTURES / "go.mod")
        assert len(graph.dependencies) >= 3
        names = {d.name for d in graph.dependencies}
        assert "gin" in names


class TestPomXml:
    def test_parse_basic(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(
            '<project><dependencies>'
            '<dependency><groupId>com.google.guava</groupId>'
            '<artifactId>guava</artifactId><version>32.0</version></dependency>'
            '</dependencies></project>'
        )
        graph = _parse_pom_xml(pom)
        assert len(graph.dependencies) == 1
        assert "guava" in graph.dependencies[0].name

    def test_parse_fixture(self):
        graph = _parse_pom_xml(FIXTURES / "pom.xml")
        assert len(graph.dependencies) >= 2
        names = {d.name for d in graph.dependencies}
        assert "spring-core" in names or any("spring" in n for n in names)

    def test_dev_scope(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(
            '<project><dependencies>'
            '<dependency><groupId>junit</groupId>'
            '<artifactId>junit</artifactId><version>4.13</version>'
            '<scope>test</scope></dependency>'
            '</dependencies></project>'
        )
        graph = _parse_pom_xml(pom)
        assert len(graph.dependencies) == 1
        assert graph.dependencies[0].is_dev is True


class TestGemspec:
    def test_parse_basic(self, tmp_path):
        gemspec = tmp_path / "test.gemspec"
        gemspec.write_text(
            'Gem::Specification.new do |spec|\n'
            '  spec.add_dependency "rails", "~> 7.0"\n'
            '  spec.add_development_dependency "rspec", "~> 3.12"\n'
            'end\n'
        )
        graph = _parse_gemspec(gemspec)
        assert len(graph.dependencies) == 2
        rails = next(d for d in graph.dependencies if d.name == "rails")
        assert rails.is_dev is False
        rspec = next(d for d in graph.dependencies if d.name == "rspec")
        assert rspec.is_dev is True

    def test_parse_fixture(self):
        graph = _parse_gemspec(FIXTURES / "test.gemspec")
        assert len(graph.dependencies) >= 4
        names = {d.name for d in graph.dependencies}
        assert "rails" in names
        assert "rspec" in names


class TestParseDirectory:
    def test_parse_directory_with_requirements(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.0\nflask==2.0\n")
        graph = parse_dependency_file(str(tmp_path))
        assert len(graph.dependencies) >= 2

    def test_parse_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            parse_dependency_file("/nonexistent/path")

    def test_parse_empty_directory(self, tmp_path):
        graph = parse_dependency_file(str(tmp_path))
        assert len(graph.dependencies) == 0
