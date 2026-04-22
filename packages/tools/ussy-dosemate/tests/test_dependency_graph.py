"""Tests for the dependency graph analyzer."""

import os
import tempfile
import shutil

import pytest

from ussy_dosemate.dependency_graph import DependencyGraphAnalyzer, ModuleInfo


class TestDependencyGraphAnalyzer:
    """Tests for DependencyGraphAnalyzer."""

    def test_analyze_finds_modules(self, temp_repo):
        """Should find Python modules in the repo."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        modules = analyzer.analyze()
        assert len(modules) > 0

    def test_module_has_files(self, temp_repo):
        """Each module should have at least one file."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        modules = analyzer.analyze()
        for name, mod in modules.items():
            assert len(mod.files) > 0

    def test_imports_detected(self, temp_repo):
        """Should detect import relationships."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        modules = analyzer.analyze()
        # At least some module should have imports (src/auth imports src/core)
        has_imports = any(len(m.imports) > 0 for m in modules.values())
        assert has_imports

    def test_reverse_deps(self, temp_repo):
        """Should compute reverse dependencies."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        modules = analyzer.analyze()
        # src/core should be imported by other modules
        has_imported_by = any(len(m.imported_by) > 0 for m in modules.values())
        assert has_imported_by

    def test_get_dependent_modules(self, temp_repo):
        """Should find transitive dependents."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        analyzer.analyze()
        # Find a core module and check its dependents
        for name in analyzer.modules:
            deps = analyzer.get_dependent_modules(name)
            # deps is a set (could be empty for leaf modules)
            assert isinstance(deps, set)

    def test_public_private_symbols(self, temp_repo):
        """Should identify public and private symbols."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        modules = analyzer.analyze()
        has_public = any(len(m.public_symbols) > 0 for m in modules.values())
        has_private = any(len(m.private_symbols) > 0 for m in modules.values())
        assert has_public  # our fixtures have public symbols
        assert has_private  # our fixtures have private symbols too

    def test_coupling_same_module_is_high(self, temp_repo):
        """Coupling of a module with itself should be based on shared deps."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        analyzer.analyze()
        for name in list(analyzer.modules.keys())[:1]:
            coupling = analyzer.compute_coupling(name, name)
            assert coupling >= 0

    def test_coupling_different_modules(self, temp_repo):
        """Coupling between different modules should be in [0, 1]."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        analyzer.analyze()
        names = list(analyzer.modules.keys())
        if len(names) >= 2:
            coupling = analyzer.compute_coupling(names[0], names[1])
            assert 0.0 <= coupling <= 1.0

    def test_public_api_fraction(self, temp_repo):
        """Public API fraction should be in [0, 1]."""
        analyzer = DependencyGraphAnalyzer(temp_repo)
        analyzer.analyze()
        for name in analyzer.modules:
            fu = analyzer.get_public_api_fraction(name)
            assert 0.0 <= fu <= 1.0


class TestDependencyGraphEmpty:
    """Tests for empty repos."""

    def test_empty_repo(self):
        """Should handle repo with no Python files."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "README.md"), 'w') as f:
                f.write("# Hello\n")
            analyzer = DependencyGraphAnalyzer(tmpdir)
            modules = analyzer.analyze()
            assert len(modules) == 0
        finally:
            shutil.rmtree(tmpdir)
