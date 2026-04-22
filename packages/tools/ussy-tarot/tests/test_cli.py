try:
    from conftest import create_fixture_dir, create_incidents_file
except ImportError:
    from .conftest import create_fixture_dir, create_incidents_file

"""Tests for tarot.cli module."""

import os
import tempfile
import pytest

from ussy_tarot.cli import main


class TestCLIVersion:
    def test_version(self):
        assert main(["version"]) == 0


class TestCLISpread:
    def test_spread_with_fixtures(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["spread", "--cards", fixture_dir, "--sims", "100", "--seed", "42"])
            assert result == 0
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_spread_json_output(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["spread", "--cards", fixture_dir, "--sims", "100", "--seed", "42", "--json"])
            assert result == 0
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_spread_no_cards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = main(["spread", "--cards", tmpdir, "--sims", "100"])
            assert result == 1

    def test_spread_nonexistent_dir(self):
        result = main(["spread", "--cards", "/nonexistent/path", "--sims", "100"])
        assert result == 1


class TestCLICards:
    def test_cards_list(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["cards", "--cards-dir", fixture_dir, "list"])
            assert result == 0
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_cards_list_verbose(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["cards", "--cards-dir", fixture_dir, "list", "--verbose"])
            assert result == 0
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_cards_show(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["cards", "--cards-dir", fixture_dir, "show", "ADR-001"])
            assert result == 0
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_cards_show_nonexistent(self):
        fixture_dir = create_fixture_dir()
        try:
            result = main(["cards", "--cards-dir", fixture_dir, "show", "ADR-999"])
            assert result == 1
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_cards_no_cards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = main(["cards", "--cards-dir", tmpdir, "list"])
            assert result == 1


class TestCLICommunity:
    def test_community_stats(self):
        result = main(["community", "stats"])
        assert result == 0

    def test_community_types(self):
        result = main(["community", "types"])
        assert result == 0

    def test_community_search(self):
        result = main(["community", "search", "Redis"])
        assert result == 0

    def test_community_search_no_keyword(self):
        result = main(["community", "search"])
        assert result == 1

    def test_community_search_no_results(self):
        result = main(["community", "search", "xyznonexistent123"])
        assert result == 0


class TestCLIEvidence:
    def test_evidence_incidents(self):
        filepath = create_incidents_file()
        try:
            result = main(["evidence", "incidents", filepath])
            assert result == 0
        finally:
            os.unlink(filepath)

    def test_evidence_summary(self):
        filepath = create_incidents_file()
        try:
            result = main(["evidence", "summary", "ADR-001", "--incidents", filepath])
            assert result == 0
        finally:
            os.unlink(filepath)

    def test_evidence_no_command(self):
        result = main(["evidence"])
        assert result == 1


class TestCLINoCommand:
    def test_no_command_shows_version(self):
        result = main([])
        assert result == 0
