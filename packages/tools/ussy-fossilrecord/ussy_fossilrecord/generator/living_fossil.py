"""Living Fossil generator: combines esolang patterns with conventional code.

Creates test cases that no human would write but that real-world tools
encounter: esolang code embedded in comments, strings, and literals of
conventional languages.
"""
from __future__ import annotations

import hashlib
import random
import string
from dataclasses import dataclass, field
from typing import Any

from ussy_fossilrecord.corpus.loader import CorpusLoader, EsolangProgram, StressCategory


@dataclass
class EmbeddedProgram:
    """An esolang program embedded in a conventional language context."""
    name: str
    host_language: str
    esolang: str
    source: str
    embedding_type: str  # "comment", "string", "literal", "chimera"
    categories: list[StressCategory] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host_language": self.host_language,
            "esolang": self.esolang,
            "source": self.source,
            "embedding_type": self.embedding_type,
            "categories": [c.value for c in self.categories],
            "metadata": self.metadata,
        }


@dataclass
class GenerationConfig:
    """Configuration for the Living Fossil generator."""
    host_languages: list[str] = field(default_factory=lambda: [
        "python", "javascript", "java", "c", "rust", "go", "ruby",
    ])
    embedding_types: list[str] = field(default_factory=lambda: [
        "comment", "string", "literal", "chimera",
    ])
    count: int = 10
    seed: int | None = None
    max_source_length: int = 2000
    extreme_nesting_depth: int = 20
    extreme_line_length: int = 1000
    symbol_density_count: int = 50

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_languages": self.host_languages,
            "embedding_types": self.embedding_types,
            "count": self.count,
            "seed": self.seed,
            "max_source_length": self.max_source_length,
            "extreme_nesting_depth": self.extreme_nesting_depth,
            "extreme_line_length": self.extreme_line_length,
            "symbol_density_count": self.symbol_density_count,
        }


# Template functions for different embedding strategies
def _embed_in_python_comment(source: str) -> str:
    """Embed esolang source in a Python comment."""
    lines = source.split("\n")
    commented = "\n".join(f"# {line}" for line in lines)
    return f'def hello():\n    """A function with embedded esolang."""\n{commented}\n    return "ok"\n'


def _embed_in_python_string(source: str) -> str:
    """Embed esolang source in a Python string."""
    escaped = source.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'esolang_code = """\n{escaped}\n"""\nprint("embedded code loaded")\n'


def _embed_in_python_literal(source: str) -> str:
    """Embed esolang source in a Python list literal."""
    chars = [f"chr({ord(c)})" for c in source[:100]]  # limit
    return f"data = [{', '.join(chars)}]\nresult = ''.join(data)\nprint(result)\n"


def _embed_in_js_comment(source: str) -> str:
    """Embed esolang source in a JavaScript comment."""
    lines = source.split("\n")
    commented = "\n".join(f"// {line}" for line in lines)
    return f'function hello() {{\n{commented}\n  return "ok";\n}}\n'


def _embed_in_js_string(source: str) -> str:
    """Embed esolang source in a JavaScript string."""
    escaped = source.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return f'const esolangCode = `{escaped}`;\nconsole.log("embedded");\n'


def _embed_in_js_literal(source: str) -> str:
    """Embed esolang source in a JS array literal."""
    chars = [str(ord(c)) for c in source[:100]]
    return f"const data = [{', '.join(chars)}];\nconst result = String.fromCharCode(...data);\nconsole.log(result);\n"


def _embed_in_java_comment(source: str) -> str:
    lines = source.split("\n")
    commented = "\n".join(f"// {line}" for line in lines)
    return f'public class Test {{\n  public static void main(String[] args) {{\n{commented}\n    System.out.println("ok");\n  }}\n}}\n'


def _embed_in_java_string(source: str) -> str:
    escaped = source.replace("\\", "\\\\").replace('"', '\\"')
    return f'public class Test {{\n  public static void main(String[] args) {{\n    String code = "{escaped}";\n    System.out.println("embedded");\n  }}\n}}\n'


def _embed_in_c_comment(source: str) -> str:
    return f'/*\n{source}\n*/\n#include <stdio.h>\nint main() {{ printf("ok\\n"); return 0; }}\n'


def _embed_in_rust_comment(source: str) -> str:
    return f'// {source}\nfn main() {{ println!("ok"); }}\n'


def _embed_in_go_comment(source: str) -> str:
    return f'// {source}\npackage main\nimport "fmt"\nfunc main() {{ fmt.Println("ok") }}\n'


def _embed_in_ruby_comment(source: str) -> str:
    lines = source.split("\n")
    commented = "\n".join(f"# {line}" for line in lines)
    return f'def hello\n{commented}\n  "ok"\nend\n'


EMBED_FUNCTIONS: dict[str, dict[str, Any]] = {
    "python": {
        "comment": _embed_in_python_comment,
        "string": _embed_in_python_string,
        "literal": _embed_in_python_literal,
    },
    "javascript": {
        "comment": _embed_in_js_comment,
        "string": _embed_in_js_string,
        "literal": _embed_in_js_literal,
    },
    "java": {
        "comment": _embed_in_java_comment,
        "string": _embed_in_java_string,
    },
    "c": {
        "comment": _embed_in_c_comment,
    },
    "rust": {
        "comment": _embed_in_rust_comment,
    },
    "go": {
        "comment": _embed_in_go_comment,
    },
    "ruby": {
        "comment": _embed_in_ruby_comment,
    },
}


class LivingFossilGenerator:
    """Generates hybrid test cases combining esolang features with conventional code."""

    def __init__(
        self,
        corpus_dir: Any = None,
        config: GenerationConfig | None = None,
    ):
        self.config = config or GenerationConfig()
        self.corpus_loader = CorpusLoader(corpus_dir)
        self._rng = random.Random(self.config.seed)

    def generate(self, count: int | None = None) -> list[EmbeddedProgram]:
        """Generate living fossil test cases.

        Args:
            count: Override the count from config.

        Returns:
            List of EmbeddedProgram instances.
        """
        n = count if count is not None else self.config.count
        programs = self.corpus_loader.programs()
        if not programs:
            return []

        results: list[EmbeddedProgram] = []

        # Strategy 1: Embed esolang in conventional languages
        results.extend(self._generate_embedded(programs, n * 2 // 5))

        # Strategy 2: Generate extreme code patterns
        results.extend(self._generate_extreme(n * 2 // 5))

        # Strategy 3: Generate chimera files (mixed syntax)
        remaining = n - len(results)
        results.extend(self._generate_chimeras(programs, remaining))

        return results[:n]

    def _generate_embedded(
        self, programs: list[EsolangProgram], count: int
    ) -> list[EmbeddedProgram]:
        """Embed esolang programs in conventional language contexts."""
        results = []
        for i in range(count):
            prog = self._rng.choice(programs)
            host = self._rng.choice(self.config.host_languages)
            embed_fns = EMBED_FUNCTIONS.get(host, {})
            embed_type = self._rng.choice(
                list(embed_fns.keys()) if embed_fns else ["comment"]
            )
            embed_fn = embed_fns.get(embed_type, _embed_in_python_comment)
            source = embed_fn(prog.source[:self.config.max_source_length])
            name = f"embedded_{host}_{prog.language}_{i}"
            results.append(EmbeddedProgram(
                name=name,
                host_language=host,
                esolang=prog.language,
                source=source,
                embedding_type=embed_type,
                categories=prog.categories,
                metadata={"original_program": prog.name},
            ))
        return results

    def _generate_extreme(self, count: int) -> list[EmbeddedProgram]:
        """Generate code with extreme nesting, line length, or symbol density."""
        results = []
        host = "python"
        for i in range(count):
            strategy = self._rng.choice(["nesting", "line_length", "symbol_density"])
            if strategy == "nesting":
                source = self._extreme_nesting()
                cats = [StressCategory.OBFUSCATED]
            elif strategy == "line_length":
                source = self._extreme_line_length()
                cats = [StressCategory.CONCISE, StressCategory.OBFUSCATED]
            else:
                source = self._extreme_symbol_density()
                cats = [StressCategory.OBFUSCATED, StressCategory.CONCISE]

            name = f"extreme_{strategy}_{i}"
            results.append(EmbeddedProgram(
                name=name,
                host_language=host,
                esolang="generated",
                source=source,
                embedding_type="extreme",
                categories=cats,
                metadata={"strategy": strategy},
            ))
        return results

    def _extreme_nesting(self) -> str:
        """Generate Python code with extreme nesting depth."""
        depth = self.config.extreme_nesting_depth
        lines = []
        for d in range(depth):
            indent = "    " * d
            lines.append(f"{indent}if True:")
        lines.append("    " * depth + "pass")
        return "\n".join(lines) + "\n"

    def _extreme_line_length(self) -> str:
        """Generate a Python file with an extremely long line."""
        length = self.config.extreme_line_length
        var_name = "x"
        parts = [str(self._rng.randint(0, 100)) for _ in range(length // 3)]
        long_line = f"{var_name} = [{', '.join(parts)}]"
        return f"# Extremely long line\n{long_line}\nprint(len({var_name}))\n"

    def _extreme_symbol_density(self) -> str:
        """Generate code with extreme symbol density."""
        symbols = "!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
        count = self.config.symbol_density_count
        chars = [self._rng.choice(symbols) for _ in range(count)]
        dense_line = "".join(chars)
        return f"# Symbol-dense line\n# {dense_line}\nprint('ok')\n"

    def _generate_chimeras(
        self, programs: list[EsolangProgram], count: int
    ) -> list[EmbeddedProgram]:
        """Generate chimera files mixing syntax from multiple languages."""
        results = []
        for i in range(count):
            if len(programs) < 2:
                continue
            chosen = self._rng.sample(programs, min(2, len(programs)))
            parts = []
            for prog in chosen:
                snippet = prog.source[:200]
                parts.append(f"# --- {prog.language} snippet ---\n{snippet}\n")
            source = "\n".join(parts)
            langs = "/".join(p.language for p in chosen)
            name = f"chimera_{langs}_{i}"
            cats = list(set(c for p in chosen for c in p.categories))
            results.append(EmbeddedProgram(
                name=name,
                host_language="mixed",
                esolang=langs,
                source=source,
                embedding_type="chimera",
                categories=cats,
                metadata={"source_languages": [p.language for p in chosen]},
            ))
        return results

    def generate_for_category(
        self, category: StressCategory, count: int = 10
    ) -> list[EmbeddedProgram]:
        """Generate living fossils targeting a specific stress category."""
        programs = self.corpus_loader.by_category(category)
        if not programs:
            return []
        return self._generate_embedded(programs, count)
