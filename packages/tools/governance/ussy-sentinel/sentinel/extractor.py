"""Pattern extraction from Python source files using the ast module.

Extracts feature vectors representing code patterns:
- Import fingerprints
- Naming distributions
- Complexity metrics
- Control flow shapes
- Structural patterns
"""

import ast
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FeatureVector:
    """A feature vector representing a code pattern in pattern space."""
    name: str
    source_file: str = ""
    source_line: int = 0
    kind: str = "function"  # function, class, module

    # Feature dimensions (all normalized 0.0 - 1.0)
    # Naming features
    name_length: float = 0.0
    name_entropy: float = 0.0
    name_snake_case: float = 0.0
    name_camel_case: float = 0.0
    avg_var_name_length: float = 0.0
    var_name_entropy: float = 0.0

    # Complexity features
    cyclomatic_complexity: float = 0.0
    nesting_depth: float = 0.0
    num_statements: float = 0.0
    num_returns: float = 0.0
    num_raises: float = 0.0
    num_loops: float = 0.0
    num_conditionals: float = 0.0

    # Structural features
    num_args: float = 0.0
    num_defaults: float = 0.0
    has_docstring: float = 0.0
    num_decorators: float = 0.0
    num_local_vars: float = 0.0

    # Control flow shape (histogram buckets)
    cf_linear: float = 0.0
    cf_branching: float = 0.0
    cf_looping: float = 0.0
    cf_exception: float = 0.0

    # Import fingerprint
    num_imports: float = 0.0
    import_stdlib_ratio: float = 0.0
    import_local_ratio: float = 0.0

    def to_list(self) -> List[float]:
        """Convert to a plain list of feature values."""
        return [
            self.name_length, self.name_entropy, self.name_snake_case,
            self.name_camel_case, self.avg_var_name_length, self.var_name_entropy,
            self.cyclomatic_complexity, self.nesting_depth, self.num_statements,
            self.num_returns, self.num_raises, self.num_loops, self.num_conditionals,
            self.num_args, self.num_defaults, self.has_docstring,
            self.num_decorators, self.num_local_vars,
            self.cf_linear, self.cf_branching, self.cf_looping, self.cf_exception,
            self.num_imports, self.import_stdlib_ratio, self.import_local_ratio,
        ]

    @classmethod
    def feature_names(cls) -> List[str]:
        """Return names of all features."""
        return [
            "name_length", "name_entropy", "name_snake_case",
            "name_camel_case", "avg_var_name_length", "var_name_entropy",
            "cyclomatic_complexity", "nesting_depth", "num_statements",
            "num_returns", "num_raises", "num_loops", "num_conditionals",
            "num_args", "num_defaults", "has_docstring",
            "num_decorators", "num_local_vars",
            "cf_linear", "cf_branching", "cf_looping", "cf_exception",
            "num_imports", "import_stdlib_ratio", "import_local_ratio",
        ]

    @classmethod
    def from_list(cls, values: List[float], name: str = "", **kwargs) -> "FeatureVector":
        """Create from a plain list of feature values."""
        keys = cls.feature_names()
        d = {k: v for k, v in zip(keys, values)}
        return cls(name=name, **d, **kwargs)


# Python stdlib module names for import classification
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
    'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii',
    'binhex', 'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb',
    'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections',
    'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib',
    'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal',
    'difflib', 'dis', 'distutils', 'doctest', 'email', 'encodings',
    'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput',
    'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
    'getpass', 'gettext', 'glob', 'gzip', 'hashlib', 'heapq', 'hmac',
    'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'imp', 'importlib',
    'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox',
    'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
    'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator',
    'optparse', 'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb',
    'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib',
    'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats',
    'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri',
    'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
    'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve',
    'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr',
    'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat',
    'statistics', 'string', 'stringprep', 'struct', 'subprocess',
    'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny',
    'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap',
    'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize',
    'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo',
    'types', 'typing', 'unicodedata', 'unittest', 'urllib', 'uu',
    'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
    'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc',
    'zipapp', 'zipfile', 'zipimport', 'zlib',
}


def _compute_entropy(text: str) -> float:
    """Compute Shannon entropy of a string, normalized to 0-1."""
    if not text:
        return 0.0
    counter = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in counter.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    # Max entropy for ASCII is log2(128) ≈ 7; normalize
    return min(1.0, entropy / 5.0)  # 5 bits is a reasonable max for code names


def _is_snake_case(name: str) -> bool:
    """Check if name follows snake_case convention."""
    return bool(re.match(r'^[a-z][a-z0-9_]*$', name)) and '__' not in name


def _is_camel_case(name: str) -> bool:
    """Check if name follows camelCase or PascalCase convention."""
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', name)) and any(
        c.isupper() for c in name[1:]
    )


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor for computing cyclomatic complexity and other metrics."""

    def __init__(self):
        self.complexity = 1  # Base complexity
        self.max_nesting = 0
        self.current_nesting = 0
        self.num_returns = 0
        self.num_raises = 0
        self.num_loops = 0
        self.num_conditionals = 0
        self.num_statements = 0
        self.local_vars: set = set()
        self.cf_linear = 0
        self.cf_branching = 0
        self.cf_looping = 0
        self.cf_exception = 0

    def _visit_branching(self, node):
        self.complexity += 1
        self.num_conditionals += 1
        self.cf_branching += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

    def visit_If(self, node):
        self._visit_branching(node)

    def visit_For(self, node):
        self.complexity += 1
        self.num_loops += 1
        self.cf_looping += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

    def visit_While(self, node):
        self.complexity += 1
        self.num_loops += 1
        self.cf_looping += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.cf_exception += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

    def visit_Return(self, node):
        self.num_returns += 1
        self.num_statements += 1
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.num_raises += 1
        self.num_statements += 1
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.num_statements += 1
        self.cf_linear += 1
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.local_vars.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self.num_statements += 1
        self.cf_linear += 1
        if isinstance(node.target, ast.Name):
            self.local_vars.add(node.target.id)
        self.generic_visit(node)

    def visit_Expr(self, node):
        self.num_statements += 1
        self.cf_linear += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        self.num_loops += 1
        self.cf_looping += 1
        for if_clause in node.ifs:
            self.complexity += 1
            self.num_conditionals += 1
        self.generic_visit(node)


def _normalize(value: float, max_val: float) -> float:
    """Normalize a value to 0.0-1.0 range."""
    if max_val <= 0:
        return 0.0
    return min(1.0, value / max_val)


def extract_function_patterns(tree: ast.AST, source_file: str = "") -> List[FeatureVector]:
    """Extract feature vectors for all function/method definitions in an AST."""
    vectors = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = ComplexityVisitor()
            visitor.visit(node)

            # Compute variable name stats
            var_names = [n for n in visitor.local_vars if not n.startswith('_')]
            avg_var_len = (sum(len(n) for n in var_names) / len(var_names)) if var_names else 0.0
            var_entropy = _compute_entropy(''.join(var_names)) if var_names else 0.0

            # Compute function name features
            fname = node.name
            name_len = len(fname)
            name_ent = _compute_entropy(fname)
            is_snake = 1.0 if _is_snake_case(fname) else 0.0
            is_camel = 1.0 if _is_camel_case(fname) else 0.0

            # Arguments
            num_args = len(node.args.args)
            num_defaults = len(node.args.defaults)

            # Docstring
            has_doc = 1.0 if (ast.get_docstring(node)) else 0.0

            # Decorators
            num_decorators = len(node.decorator_list)

            # Control flow normalization
            total_cf = visitor.cf_linear + visitor.cf_branching + visitor.cf_looping + visitor.cf_exception
            cf_lin = visitor.cf_linear / total_cf if total_cf > 0 else 0.5
            cf_br = visitor.cf_branching / total_cf if total_cf > 0 else 0.0
            cf_lo = visitor.cf_looping / total_cf if total_cf > 0 else 0.0
            cf_ex = visitor.cf_exception / total_cf if total_cf > 0 else 0.0

            vec = FeatureVector(
                name=fname,
                source_file=source_file,
                source_line=node.lineno,
                kind="function",
                name_length=_normalize(name_len, 30),
                name_entropy=name_ent,
                name_snake_case=is_snake,
                name_camel_case=is_camel,
                avg_var_name_length=_normalize(avg_var_len, 20),
                var_name_entropy=var_entropy,
                cyclomatic_complexity=_normalize(visitor.complexity, 20),
                nesting_depth=_normalize(visitor.max_nesting, 8),
                num_statements=_normalize(visitor.num_statements, 50),
                num_returns=_normalize(visitor.num_returns, 5),
                num_raises=_normalize(visitor.num_raises, 5),
                num_loops=_normalize(visitor.num_loops, 5),
                num_conditionals=_normalize(visitor.num_conditionals, 10),
                num_args=_normalize(num_args, 8),
                num_defaults=_normalize(num_defaults, 5),
                has_docstring=has_doc,
                num_decorators=_normalize(num_decorators, 4),
                num_local_vars=_normalize(len(visitor.local_vars), 20),
                cf_linear=cf_lin,
                cf_branching=cf_br,
                cf_looping=cf_lo,
                cf_exception=cf_ex,
            )
            vectors.append(vec)

    return vectors


def extract_class_patterns(tree: ast.AST, source_file: str = "") -> List[FeatureVector]:
    """Extract feature vectors for all class definitions in an AST."""
    vectors = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Aggregate metrics from methods
            method_count = 0
            total_complexity = 0
            total_methods = 0
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_count += 1
                    v = ComplexityVisitor()
                    v.visit(item)
                    total_complexity += v.complexity

            cname = node.name
            name_len = len(cname)
            name_ent = _compute_entropy(cname)
            is_camel = 1.0 if _is_camel_case(cname) else 0.0
            is_snake = 1.0 if _is_snake_case(cname) else 0.0

            # Bases
            num_bases = len(node.bases)

            vec = FeatureVector(
                name=cname,
                source_file=source_file,
                source_line=node.lineno,
                kind="class",
                name_length=_normalize(name_len, 30),
                name_entropy=name_ent,
                name_snake_case=is_snake,
                name_camel_case=is_camel,
                avg_var_name_length=0.0,
                var_name_entropy=0.0,
                cyclomatic_complexity=_normalize(total_complexity / max(method_count, 1), 20),
                nesting_depth=0.0,
                num_statements=_normalize(method_count, 20),
                num_returns=0.0,
                num_raises=0.0,
                num_loops=0.0,
                num_conditionals=0.0,
                num_args=_normalize(num_bases, 5),
                num_defaults=0.0,
                has_docstring=1.0 if ast.get_docstring(node) else 0.0,
                num_decorators=_normalize(len(node.decorator_list), 4),
                num_local_vars=0.0,
                cf_linear=0.0,
                cf_branching=0.0,
                cf_looping=0.0,
                cf_exception=0.0,
            )
            vectors.append(vec)

    return vectors


def extract_module_patterns(tree: ast.AST, source_file: str = "") -> FeatureVector:
    """Extract a single feature vector for the entire module."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split('.')[0])

    import_counter = Counter(imports)
    total_imports = len(imports)
    stdlib_count = sum(c for mod, c in import_counter.items() if mod in STDLIB_MODULES)
    stdlib_ratio = stdlib_count / total_imports if total_imports > 0 else 0.0
    local_ratio = 1.0 - stdlib_ratio  # Approximation

    # Count top-level items
    func_count = sum(1 for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    class_count = sum(1 for n in tree.body if isinstance(n, ast.ClassDef))

    vec = FeatureVector(
        name=os.path.basename(source_file) if source_file else "<module>",
        source_file=source_file,
        source_line=0,
        kind="module",
        name_length=0.0,
        name_entropy=0.0,
        name_snake_case=0.0,
        name_camel_case=0.0,
        avg_var_name_length=0.0,
        var_name_entropy=0.0,
        cyclomatic_complexity=0.0,
        nesting_depth=0.0,
        num_statements=_normalize(func_count + class_count, 20),
        num_returns=0.0,
        num_raises=0.0,
        num_loops=0.0,
        num_conditionals=0.0,
        num_args=0.0,
        num_defaults=0.0,
        has_docstring=1.0 if ast.get_docstring(tree) else 0.0,
        num_decorators=0.0,
        num_local_vars=0.0,
        cf_linear=0.0,
        cf_branching=0.0,
        cf_looping=0.0,
        cf_exception=0.0,
        num_imports=_normalize(total_imports, 30),
        import_stdlib_ratio=stdlib_ratio,
        import_local_ratio=local_ratio,
    )
    return vec


def extract_patterns_from_source(source: str, source_file: str = "",
                                  granularity: str = "function") -> List[FeatureVector]:
    """Extract all patterns from a Python source string.

    Args:
        source: Python source code string
        source_file: Name of the source file
        granularity: One of 'function', 'class', 'module'

    Returns:
        List of FeatureVector instances
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    vectors = []

    if granularity in ("function", "class"):
        vectors.extend(extract_function_patterns(tree, source_file))

    if granularity in ("class",):
        vectors.extend(extract_class_patterns(tree, source_file))

    if granularity == "module":
        vectors.append(extract_module_patterns(tree, source_file))

    return vectors


def extract_patterns_from_file(filepath: str, granularity: str = "function") -> List[FeatureVector]:
    """Extract patterns from a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except (IOError, OSError):
        return []

    return extract_patterns_from_source(source, source_file=filepath, granularity=granularity)


def extract_patterns_from_directory(dirpath: str, granularity: str = "function") -> List[FeatureVector]:
    """Extract patterns from all Python files in a directory tree."""
    vectors = []
    for root, dirs, files in os.walk(dirpath):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git', 'venv', '.venv')]
        for fname in sorted(files):
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                vectors.extend(extract_patterns_from_file(fpath, granularity))
    return vectors
