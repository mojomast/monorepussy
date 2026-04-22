"""Tests for operon.cli module."""

import json
import tempfile
from pathlib import Path

import pytest

from operon.cli import (
    cmd_enhance,
    cmd_epigenetics,
    cmd_express,
    cmd_map,
    cmd_promote,
    cmd_repress,
    create_parser,
    main,
)
from operon.storage import StorageManager


class TestCreateParser:
    def test_parser_creation(self):
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "operon"

    def test_parser_map_command(self):
        parser = create_parser()
        args = parser.parse_args(["map", "/tmp"])
        assert args.command == "map"
        assert args.path == "/tmp"

    def test_parser_promote_command(self):
        parser = create_parser()
        args = parser.parse_args(["promote", "api_change"])
        assert args.command == "promote"
        assert args.change == "api_change"

    def test_parser_repress_command(self):
        parser = create_parser()
        args = parser.parse_args(["repress", "old.py", "--type", "inducible"])
        assert args.command == "repress"
        assert args.feature == "old.py"
        assert args.type == "inducible"

    def test_parser_enhance_command(self):
        parser = create_parser()
        args = parser.parse_args(["enhance", "/tmp"])
        assert args.command == "enhance"
        assert args.path == "/tmp"

    def test_parser_express_command(self):
        parser = create_parser()
        args = parser.parse_args(["express", "operon_0", "--audience", "beginner"])
        assert args.command == "express"
        assert args.operon == "operon_0"
        assert args.audience == "beginner"

    def test_parser_epigenetics_command(self):
        parser = create_parser()
        args = parser.parse_args(["epigenetics"])
        assert args.command == "epigenetics"

    def test_parser_default_db(self):
        parser = create_parser()
        args = parser.parse_args(["map", "/tmp"])
        assert args.db == "operon.db"

    def test_parser_json_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--json", "map", "/tmp"])
        assert args.json is True

    def test_parser_version(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_no_command(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestCmdMap:
    def test_map_nonexistent_path(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["map", "/nonexistent/path"])
        result = cmd_map(args, storage)
        assert "error" in result

    def test_map_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module.py").write_text("def func(): pass\n")
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["map", tmpdir])
            result = cmd_map(args, storage)
            assert result["command"] == "map"
            assert result["genes_found"] >= 1

    def test_map_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def main(): pass\n")
            f.flush()
            path = Path(f.name)
        try:
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["map", str(path)])
            result = cmd_map(args, storage)
            assert result["genes_found"] == 1
        finally:
            path.unlink()

    def test_map_with_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text("def a(): pass\n")
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["map", tmpdir, "--threshold", "0.5"])
            result = cmd_map(args, storage)
            assert result["threshold"] == 0.5


class TestCmdPromote:
    def test_promote_basic(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["promote", "public_api_change"])
        result = cmd_promote(args, storage)
        assert result["command"] == "promote"
        assert result["change"] == "public_api_change"
        assert result["strength"] == 1.0

    def test_promote_with_codebase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module.py").write_text("def func(): pass\n")
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["promote", "public_api_change", "--codebase", tmpdir])
            result = cmd_promote(args, storage)
            assert result["command"] == "promote"


class TestCmdRepress:
    def test_repress_apply(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["repress", "old.py", "--type", "inducible"])
        result = cmd_repress(args, storage)
        assert result["command"] == "repress"
        assert result["action"] == "apply"
        assert result["repressor_type"] == "inducible"
        assert "repressor_id" in result

    def test_repress_lift(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["repress", "old.py", "--lift"])
        result = cmd_repress(args, storage)
        assert result["action"] == "lift"
        assert result["success"] is False  # no repressor to lift yet

    def test_repress_constitutive(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["repress", "util.py", "--type", "constitutive"])
        result = cmd_repress(args, storage)
        assert result["repressor_type"] == "constitutive"


class TestCmdEnhance:
    def test_enhance_nonexistent(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["enhance", "/nonexistent"])
        result = cmd_enhance(args, storage)
        assert "error" in result

    def test_enhance_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text("def a(): pass\n")
            (Path(tmpdir) / "b.py").write_text("def b(): pass\n")
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["enhance", tmpdir, "--top", "5"])
            result = cmd_enhance(args, storage)
            assert result["command"] == "enhance"
            assert args.top == 5

    def test_enhance_top_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text("def a(): pass\n")
            storage = StorageManager(":memory:")
            args = create_parser().parse_args(["enhance", tmpdir])
            result = cmd_enhance(args, storage)
            assert result["command"] == "enhance"


class TestCmdExpress:
    def test_express_missing_operon(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["express", "missing_op", "--audience", "expert"])
        result = cmd_express(args, storage)
        assert "error" in result
        assert result["error"] == "Operon not found: missing_op"

    def test_express_with_operon(self):
        storage = StorageManager(":memory:")
        from operon.models import Gene, Operon
        from operon.mapper import OperonMapper

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text('"""Auth module."""\ndef login(): pass\n')
            codebase = OperonMapper().map_operons(type("obj", (), {"root_path": tmpdir, "genes": [], "operons": [], "deprecated_features": [], "internal_apis": []})())
            # Actually create a proper Codebase
            from operon.models import Codebase
            cb = Codebase(root_path=tmpdir)
            mapper = OperonMapper()
            operons = mapper.map_operons(cb)
            for o in operons:
                storage.save_operon(o)

            args = create_parser().parse_args(["express", "operon_0", "--audience", "beginner"])
            result = cmd_express(args, storage)
            assert result["command"] == "express"
            assert result["operon"] == "operon_0"


class TestCmdEpigenetics:
    def test_epigenetics_empty(self):
        storage = StorageManager(":memory:")
        args = create_parser().parse_args(["epigenetics"])
        result = cmd_epigenetics(args, storage)
        assert result["command"] == "epigenetics"
        assert result["marks_count"] == 0

    def test_epigenetics_with_operon_filter(self):
        storage = StorageManager(":memory:")
        from operon.models import Gene, Operon
        operon = Operon(operon_id="op_0", genes=[Gene(name="old", path="old.py", is_deprecated=True)])
        storage.save_operon(operon)
        args = create_parser().parse_args(["epigenetics", "--operon", "op_0"])
        result = cmd_epigenetics(args, storage)
        assert result["command"] == "epigenetics"


class TestMain:
    def test_main_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_main_no_command(self, capsys):
        code = main([])
        assert code == 0

    def test_main_map_json(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module.py").write_text("def func(): pass\n")
            code = main(["--json", "map", tmpdir])
            assert code == 0
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["command"] == "map"

    def test_main_promote_json(self, capsys):
        code = main(["--json", "promote", "public_api_change"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["strength"] == 1.0

    def test_main_repress_json(self, capsys):
        code = main(["--json", "repress", "old.py"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["action"] == "apply"

    def test_main_enhance_json(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text("def a(): pass\n")
            code = main(["--json", "enhance", tmpdir])
            assert code == 0
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["command"] == "enhance"

    def test_main_epigenetics_json(self, capsys):
        code = main(["--json", "epigenetics"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["command"] == "epigenetics"

    def test_main_express_missing(self, capsys):
        code = main(["--json", "express", "nonexistent"])
        assert code == 1

    def test_main_unknown_command(self):
        # argparse handles unknown commands by erroring
        with pytest.raises(SystemExit):
            main(["unknown"])
