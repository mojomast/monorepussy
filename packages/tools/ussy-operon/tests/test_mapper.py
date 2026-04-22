"""Tests for operon.mapper module."""

import tempfile
from pathlib import Path

import pytest

from operon.mapper import OperonMapper
from operon.models import Codebase, Gene


class TestOperonMapper:
    def test_mapper_creation(self):
        mapper = OperonMapper(coupling_threshold=0.5)
        assert mapper.coupling_threshold == 0.5

    def test_is_python_file_true(self):
        mapper = OperonMapper()
        assert mapper._is_python_file(Path("module.py")) is True

    def test_is_python_file_test_file(self):
        mapper = OperonMapper()
        assert mapper._is_python_file(Path("test_module.py")) is False

    def test_is_python_file_init(self):
        mapper = OperonMapper()
        assert mapper._is_python_file(Path("__init__.py")) is False

    def test_is_python_file_not_py(self):
        mapper = OperonMapper()
        assert mapper._is_python_file(Path("README.md")) is False

    def test_parse_gene_valid(self):
        mapper = OperonMapper()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('"""Module docstring."""\nimport os\ndef func(): pass\n')
            f.flush()
            path = Path(f.name)
        try:
            gene = mapper._parse_gene(path, path.parent)
            assert gene is not None
            assert gene.name == path.stem
            assert gene.docstring == "Module docstring."
            assert "os" in gene.imports
        finally:
            path.unlink()

    def test_parse_gene_deprecated(self):
        mapper = OperonMapper()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('"""Old module. DEPRECATED"""\ndef old(): pass\n')
            f.flush()
            path = Path(f.name)
        try:
            gene = mapper._parse_gene(path, path.parent)
            assert gene is not None
            assert gene.is_deprecated is True
        finally:
            path.unlink()

    def test_parse_gene_internal(self):
        mapper = OperonMapper()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('"""Internal module."""\n# internal use only\ndef helper(): pass\n')
            f.flush()
            path = Path(f.name)
        try:
            gene = mapper._parse_gene(path, path.parent)
            assert gene is not None
            assert gene.is_internal is True
        finally:
            path.unlink()

    def test_structural_coupling(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", imports=["os", "json"])
        g2 = Gene(name="b", path="b.py", imports=["os", "sys"])
        coupling = mapper._structural_coupling([g1, g2])
        assert ("a.py", "b.py") in coupling or ("b.py", "a.py") in coupling

    def test_structural_coupling_no_shared(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", imports=["os"])
        g2 = Gene(name="b", path="b.py", imports=["sys"])
        coupling = mapper._structural_coupling([g1, g2])
        # Coupling exists but score is 0.0
        assert ("a.py", "b.py") in coupling or ("b.py", "a.py") in coupling
        assert coupling.get(("a.py", "b.py"), coupling.get(("b.py", "a.py"))) == 0.0

    def test_temporal_coupling(self):
        mapper = OperonMapper()
        g1 = Gene(name="auth", path="auth.py")
        g2 = Gene(name="auth_utils", path="auth_utils.py")
        coupling = mapper._temporal_coupling([g1, g2])
        assert ("auth.py", "auth_utils.py") in coupling or ("auth_utils.py", "auth.py") in coupling

    def test_call_coupling(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", imports=["b.helper"])
        g2 = Gene(name="b", path="b.py", exports=["helper"])
        coupling = mapper._call_coupling([g1, g2])
        assert ("a.py", "b.py") in coupling

    def test_combine_graphs(self):
        mapper = OperonMapper()
        s = {("a", "b"): 0.5}
        t = {("a", "b"): 0.3}
        c = {("a", "b"): 0.8}
        combined = mapper._combine_graphs(s, t, c)
        assert ("a", "b") in combined
        # 0.4 * 0.5 + 0.2 * 0.3 + 0.4 * 0.8 = 0.2 + 0.06 + 0.32 = 0.58
        assert combined[("a", "b")] == pytest.approx(0.58, rel=0.01)

    def test_detect_communities_empty(self):
        mapper = OperonMapper()
        communities = mapper._detect_communities([], {})
        assert communities == []

    def test_detect_communities_single(self):
        mapper = OperonMapper()
        g = Gene(name="a", path="a.py")
        communities = mapper._detect_communities([g], {})
        assert len(communities) == 1
        assert communities[0][0].path == "a.py"

    def test_find_entry_points(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", exports=["main", "helper", "util"])
        g2 = Gene(name="b", path="b.py", exports=["run"])
        entry = mapper._find_entry_points([g1, g2])
        assert "a.py" in entry  # a.py has more exports

    def test_find_control_points(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", imports=["b.func"])
        g2 = Gene(name="b", path="b.py", imports=[])
        control = mapper._find_control_points([g1, g2])
        assert "a.py" in control  # a imports from b

    def test_find_external_dependencies(self):
        mapper = OperonMapper()
        g1 = Gene(name="a", path="a.py", imports=["os.path", "json"])
        g2 = Gene(name="b", path="b.py", imports=["sys"])
        external = mapper._find_external_dependencies([g1, g2])
        assert "os" in external
        assert "json" in external

    def test_map_operons_empty_directory(self):
        mapper = OperonMapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            codebase = Codebase(root_path=tmpdir)
            operons = mapper.map_operons(codebase)
            assert operons == []

    def test_map_operons_single_file(self):
        mapper = OperonMapper()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('def main(): pass\n')
            f.flush()
            path = Path(f.name)
        try:
            codebase = Codebase(root_path=str(path))
            operons = mapper.map_operons(codebase)
            assert len(operons) == 1
            assert operons[0].operon_id == "operon_0"
        finally:
            path.unlink()

    def test_map_operons_directory(self):
        mapper = OperonMapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple Python files
            (Path(tmpdir) / "auth.py").write_text('import os\ndef login(): pass\n')
            (Path(tmpdir) / "utils.py").write_text('import os\ndef helper(): pass\n')
            codebase = Codebase(root_path=tmpdir)
            operons = mapper.map_operons(codebase)
            # Both files import os, so should be coupled
            assert len(operons) >= 1

    def test_map_operons_captures_deprecated(self):
        mapper = OperonMapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "old.py").write_text('"""DEPRECATED module."""\ndef old(): pass\n')
            codebase = Codebase(root_path=tmpdir)
            mapper.map_operons(codebase)
            assert len(codebase.deprecated_features) == 1

    def test_map_operons_captures_internal(self):
        mapper = OperonMapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "_internal.py").write_text('"""Internal module."""\n# internal\ndef helper(): pass\n')
            codebase = Codebase(root_path=tmpdir)
            mapper.map_operons(codebase)
            assert len(codebase.internal_apis) == 1
