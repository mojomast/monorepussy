"""Tests for snapshot export and import."""

import json
import os
import tarfile
import tempfile
from pathlib import Path

import pytest

from ussy_snapshot.export import export_snapshot, import_snapshot
from ussy_snapshot.models import (
    Snapshot,
    SnapshotMetadata,
    TerminalState,
    EditorState,
    OpenFile,
    EnvironmentState,
    MentalContext,
)
from ussy_snapshot.storage import save_snapshot, load_snapshot


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    old_env = os.environ.get("SNAPSHOT_DIR")
    os.environ["SNAPSHOT_DIR"] = str(snap_dir)
    yield snap_dir
    if old_env is not None:
        os.environ["SNAPSHOT_DIR"] = old_env
    else:
        os.environ.pop("SNAPSHOT_DIR", None)


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def sample_snapshot(storage_dir):
    """Create and save a sample snapshot."""
    snap = Snapshot(
        name="export-test",
        metadata=SnapshotMetadata(name="export-test"),
        terminals=[TerminalState(session_id="t1", working_directory="/tmp")],
        mental_context=MentalContext(note="export test note"),
        environment=EnvironmentState(variables={"HOME": "/tmp", "API_KEY": "secret123"}),
    )
    save_snapshot(snap)
    return snap


class TestExportSnapshot:
    def test_export_creates_tarball(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        result = export_snapshot("export-test", output_path=output)
        assert os.path.exists(result)
        assert result.endswith(".tar.gz")

    def test_export_default_path(self, storage_dir, sample_snapshot):
        os.chdir("/tmp")
        result = export_snapshot("export-test")
        assert os.path.exists(result)
        os.unlink(result)  # cleanup

    def test_export_contains_snapshot_json(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()
            assert "snapshot.json" in names

    def test_export_contains_env_script(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()
            assert "env_restore.sh" in names

    def test_export_contains_readme(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()
            assert "README.txt" in names

    def test_export_sanitizes_secrets(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        with tarfile.open(output, "r:gz") as tar:
            f = tar.extractfile("snapshot.json")
            data = json.loads(f.read().decode("utf-8"))
            assert "API_KEY" not in data["environment"]["variables"]

    def test_export_includes_secrets(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output, include_secrets=True)
        with tarfile.open(output, "r:gz") as tar:
            f = tar.extractfile("snapshot.json")
            data = json.loads(f.read().decode("utf-8"))
            assert "API_KEY" in data["environment"]["variables"]

    def test_export_nonexistent_snapshot(self, storage_dir, output_dir):
        with pytest.raises(ValueError, match="not found"):
            export_snapshot("no-such-snap", output_path=str(output_dir / "out.tar.gz"))


class TestImportSnapshot:
    def test_import_creates_snapshot(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        name = import_snapshot(output)
        assert name == "export-test"
        # Verify it was saved
        loaded = load_snapshot("export-test")
        assert loaded is not None

    def test_import_with_new_name(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        name = import_snapshot(output, new_name="imported-snap")
        assert name == "imported-snap"
        loaded = load_snapshot("imported-snap")
        assert loaded is not None

    def test_import_nonexistent_archive(self, storage_dir):
        with pytest.raises(FileNotFoundError):
            import_snapshot("/nonexistent/path.tar.gz")

    def test_import_preserves_data(self, storage_dir, output_dir, sample_snapshot):
        output = str(output_dir / "test.tar.gz")
        export_snapshot("export-test", output_path=output)
        # Delete original
        from ussy_snapshot.storage import delete_snapshot
        delete_snapshot("export-test")
        # Import
        name = import_snapshot(output)
        loaded = load_snapshot(name)
        assert loaded.mental_context.note == "export test note"

    def test_export_import_roundtrip(self, storage_dir, output_dir):
        original = Snapshot(
            name="roundtrip",
            metadata=SnapshotMetadata(name="roundtrip", tags=["important"]),
            terminals=[TerminalState(session_id="t1", working_directory="/home")],
            editor=EditorState(open_files=[OpenFile(path="main.py")]),
            mental_context=MentalContext(note="round trip note"),
        )
        save_snapshot(original)
        output = str(output_dir / "roundtrip.tar.gz")
        export_snapshot("roundtrip", output_path=output)
        
        # Delete and re-import
        from ussy_snapshot.storage import delete_snapshot
        delete_snapshot("roundtrip")
        name = import_snapshot(output)
        loaded = load_snapshot(name)
        
        assert loaded.name == "roundtrip"
        assert loaded.mental_context.note == "round trip note"
        assert len(loaded.terminals) == 1
        assert len(loaded.editor.open_files) == 1
