"""Tests for curator.cli."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_curator import cli


class TestCatalogCommand:
    def test_catalog_existing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: T\n---\n")
        assert cli.cmd_catalog(type("Args", (), {"path": str(f)})) == 0
        captured = capsys.readouterr()
        assert "MARC Record" in captured.out

    def test_catalog_missing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert cli.cmd_catalog(type("Args", (), {"path": str(tmp_path / "missing.md")})) == 1


class TestClassifyCommand:
    def test_classify_existing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Title\n")
        assert cli.cmd_classify(type("Args", (), {"path": str(f)})) == 0
        captured = capsys.readouterr()
        assert "Classification" in captured.out


class TestConditionCommand:
    def test_condition_existing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Content.")
        assert cli.cmd_condition(type("Args", (), {"path": str(f)})) == 0
        captured = capsys.readouterr()
        assert "Conservation Report" in captured.out


class TestProvenanceCommand:
    def test_provenance_existing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Content.")
        assert cli.cmd_provenance(type("Args", (), {"path": str(f)})) == 0
        captured = capsys.readouterr()
        assert "Provenance" in captured.out


class TestExhibitCommand:
    def test_exhibit_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        (tmp_path / "b.md").write_text("# B\n")
        args = type("Args", (), {"target": str(tmp_path), "theme": "general", "audience": "general", "max_items": 5})
        assert cli.cmd_exhibit(args) == 0
        captured = capsys.readouterr()
        assert "Exhibition" in captured.out

    def test_exhibit_empty(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        args = type("Args", (), {"target": str(tmp_path), "theme": "general", "audience": "general", "max_items": 5})
        assert cli.cmd_exhibit(args) == 0
        captured = capsys.readouterr()
        assert "No documents found" in captured.out


class TestWeedCommand:
    def test_weed_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        args = type("Args", (), {"target": str(tmp_path), "threshold": 0.99, "dry_run": True})
        assert cli.cmd_weed(args) == 0
        captured = capsys.readouterr()
        assert "Weeding Report" in captured.out


class TestShelfCommand:
    def test_shelf_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        args = type("Args", (), {"target": str(tmp_path), "facet": None})
        assert cli.cmd_shelf(args) == 0
        captured = capsys.readouterr()
        assert "Shelf Browse" in captured.out

    def test_shelf_with_facet_filter(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        args = type("Args", (), {"target": str(tmp_path), "facet": "AUD:general"})
        assert cli.cmd_shelf(args) == 0


class TestAuditCommand:
    def test_audit_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        args = type("Args", (), {"target": str(tmp_path), "json": False})
        assert cli.cmd_audit(args) == 0
        captured = capsys.readouterr()
        assert "Collection Health Audit" in captured.out

    def test_audit_json(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "a.md").write_text("# A\n")
        args = type("Args", (), {"target": str(tmp_path), "json": True})
        assert cli.cmd_audit(args) == 0
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "document_count" in data


class TestMain:
    def test_main_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert cli.main([]) == 1
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "curator" in captured.out.lower()

    def test_main_catalog(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: T\n---\n")
        assert cli.main(["catalog", str(f)]) == 0

    def test_main_classify(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Title\n")
        assert cli.main(["classify", str(f)]) == 0
