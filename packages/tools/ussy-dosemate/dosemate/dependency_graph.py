"""Dependency graph analyzer — maps module dependencies and coupling."""

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class ModuleInfo:
    """Information about a code module."""
    name: str
    files: List[str] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    public_symbols: Set[str] = field(default_factory=set)
    private_symbols: Set[str] = field(default_factory=set)


class DependencyGraphAnalyzer:
    """Analyze import/dependency relationships between modules."""

    # Python import patterns
    IMPORT_PATTERNS = [
        re.compile(r'^\s*import\s+([a-zA-Z_][\w.]*)', re.MULTILINE),
        re.compile(r'^\s*from\s+([a-zA-Z_][\w.]*)\s+import', re.MULTILINE),
    ]

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self.modules: Dict[str, ModuleInfo] = {}
        self._file_to_module: Dict[str, str] = {}

    def analyze(self) -> Dict[str, ModuleInfo]:
        """Analyze the repo and build the dependency graph."""
        self._scan_files()
        self._parse_imports()
        self._resolve_reverse_deps()
        self._identify_symbols()
        return self.modules

    def _scan_files(self):
        """Walk the repo and catalog Python files."""
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.tox', 'venv', '.venv', 'env'}
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for f in files:
                if f.endswith('.py'):
                    filepath = os.path.join(root, f)
                    relpath = os.path.relpath(filepath, self.repo_path)
                    # Module = top 2 path components or "root"
                    parts = relpath.replace(os.sep, '/').split('/')
                    if len(parts) > 1:
                        module_name = '/'.join(parts[:2])
                    else:
                        module_name = 'root'
                    self._file_to_module[relpath] = module_name
                    if module_name not in self.modules:
                        self.modules[module_name] = ModuleInfo(name=module_name)
                    self.modules[module_name].files.append(relpath)

    def _parse_imports(self):
        """Parse import statements from each module's files."""
        for module_name, module_info in self.modules.items():
            for filepath in module_info.files:
                fullpath = os.path.join(self.repo_path, filepath)
                try:
                    with open(fullpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except (OSError, IOError):
                    continue
                for pattern in self.IMPORT_PATTERNS:
                    for match in pattern.finditer(content):
                        import_path = match.group(1).split('.')[0]
                        # Only count imports that map to known modules
                        for other_mod in self.modules:
                            if import_path in other_mod or other_mod.startswith(import_path):
                                module_info.imports.add(other_mod)

    def _resolve_reverse_deps(self):
        """Build reverse dependency map (who imports whom)."""
        for module_name, module_info in self.modules.items():
            for imported in module_info.imports:
                if imported in self.modules and imported != module_name:
                    self.modules[imported].imported_by.add(module_name)

    def _identify_symbols(self):
        """Identify public and private symbols in each module."""
        # Simple heuristic: functions/classes starting with _ are private
        symbol_pattern = re.compile(r'^(?:def|class)\s+([a-zA-Z_]\w*)', re.MULTILINE)
        for module_name, module_info in self.modules.items():
            for filepath in module_info.files:
                fullpath = os.path.join(self.repo_path, filepath)
                try:
                    with open(fullpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except (OSError, IOError):
                    continue
                for match in symbol_pattern.finditer(content):
                    symbol = match.group(1)
                    if symbol.startswith('_'):
                        module_info.private_symbols.add(symbol)
                    else:
                        module_info.public_symbols.add(symbol)

    def get_dependent_modules(self, module_name: str) -> Set[str]:
        """Get all modules that depend on the given module (transitive)."""
        visited = set()
        stack = [module_name]
        while stack:
            current = stack.pop()
            if current in visited or current not in self.modules:
                continue
            visited.add(current)
            for dep in self.modules[current].imported_by:
                if dep not in visited:
                    stack.append(dep)
        visited.discard(module_name)
        return visited

    def get_dependency_count(self, module_name: str) -> int:
        """Count direct dependents of a module."""
        if module_name in self.modules:
            return len(self.modules[module_name].imported_by)
        return 0

    def compute_coupling(self, module_a: str, module_b: str) -> float:
        """Compute coupling coefficient between two modules (0 to 1).

        Based on shared dependencies and dependents.
        """
        if module_a not in self.modules or module_b not in self.modules:
            return 0.0
        a_deps = self.modules[module_a].imports | self.modules[module_a].imported_by
        b_deps = self.modules[module_b].imports | self.modules[module_b].imported_by
        if not a_deps and not b_deps:
            return 0.0
        intersection = a_deps & b_deps
        union = a_deps | b_deps
        return len(intersection) / len(union) if union else 0.0

    def get_public_api_fraction(self, module_name: str) -> float:
        """Compute the fraction of symbols that are public (unbound fraction fu)."""
        if module_name not in self.modules:
            return 0.0
        m = self.modules[module_name]
        total = len(m.public_symbols) + len(m.private_symbols)
        if total == 0:
            return 0.5  # default
        return len(m.public_symbols) / total

    def get_total_dependent_modules(self) -> int:
        """Total number of modules that have at least one dependent."""
        return sum(1 for m in self.modules.values() if m.imported_by)
