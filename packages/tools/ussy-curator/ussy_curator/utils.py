"""Shared utilities for Curator."""

from __future__ import annotations

import re
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_yaml_frontmatter(path: Path) -> dict[str, Any]:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = parts[1]
    result: dict[str, Any] = {}
    for line in fm.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            result[key] = value
    return result


def infer_title(path: Path, content: str = "") -> str:
    """Infer a document title from its content or filename."""
    if not content and path.exists():
        content = path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def infer_author(path: Path, content: str = "") -> str:
    """Infer author from frontmatter or file metadata."""
    fm = parse_yaml_frontmatter(path)
    author = fm.get("author", "")
    if author:
        return str(author)
    return "unknown"


def git_creation_date(path: Path) -> str:
    """Return file creation date as ISO string (uses ctime fallback)."""
    if not path.exists():
        return datetime.now(timezone.utc).isoformat()
    stat = path.stat()
    dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
    return dt.isoformat()


def git_last_edit(path: Path) -> datetime:
    """Return last modification time (uses mtime fallback)."""
    if not path.exists():
        return datetime.now(timezone.utc)
    stat = path.stat()
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def classify_doc_type(path: Path) -> str:
    """Classify document type from extension and content."""
    suffix = path.suffix.lower()
    mapping = {
        ".md": "markdown",
        ".rst": "restructuredtext",
        ".txt": "plain_text",
        ".py": "python_docstring",
        ".ipynb": "jupyter_notebook",
    }
    return mapping.get(suffix, "unknown")


def extract_markdown_links(path: Path) -> list[Any]:
    """Extract markdown links from a file."""
    from ussy_curator.models import Link
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = []
    for m in re.finditer(pattern, text):
        target_str = m.group(2)
        if target_str.startswith("http"):
            continue
        target = (path.parent / target_str).resolve()
        links.append(Link(source=path, target=target, text=m.group(1)))
    return links


def extract_keywords(content: str) -> list[str]:
    """Extract simple keywords from content."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
    stopwords = {
        "this", "that", "with", "from", "they", "have", "were", "been",
        "their", "would", "there", "could", "should", "about", "which",
        "when", "where", "what", "how", "why", "who", "will", "shall",
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "had", "her", "his", "was", "one", "our", "out", "day", "get",
        "has", "him", "his", "how", "its", "may", "new", "now", "old",
        "see", "two", "way", "who", "boy", "did", "she", "use", "her",
        "than", "them", "well", "were", "said", "each", "over", "also",
    }
    freq: dict[str, int] = {}
    for w in words:
        if w in stopwords:
            continue
        freq[w] = freq.get(w, 0) + 1
    # Return top keywords by frequency
    sorted_kw = sorted(freq, key=lambda k: freq[k], reverse=True)
    return sorted_kw[:20]


def make_summary(content: str, max_len: int = 200) -> str:
    """Create a short summary from content."""
    return adapt_summary(content, max_len)


def adapt_summary(content: str, max_len: int = 200, complexity: str = "standard") -> str:
    """Adapt a summary to a target length and complexity."""
    text = re.sub(r"[#*`\[\]\(\)]", "", content)
    text = re.sub(r"\s+", " ", text).strip()
    if complexity == "simple":
        # Remove parentheticals and complex punctuation for simplicity
        text = re.sub(r"\([^)]*\)", "", text)
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return truncated + "..."


def flesch_reading_ease(content: str) -> float:
    """Compute Flesch Reading Ease score."""
    sentences = re.split(r"[.!?]+", content)
    sentences = [s for s in sentences if s.strip()]
    words = re.findall(r"\b\w+\b", content)
    syllables = sum(_count_syllables(w) for w in words)
    if not sentences or not words:
        return 0.0
    avg_sentence_length = len(words) / len(sentences)
    avg_syllables_per_word = syllables / len(words)
    return 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)


def _count_syllables(word: str) -> int:
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    return max(1, count)


def jaccard_similarity(a: set[Any], b: set[Any]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    keys = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def vectorize(text: str) -> dict[str, float]:
    """Create a simple TF vector from text."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    vec: dict[str, float] = {}
    for w in words:
        vec[w] = vec.get(w, 0.0) + 1.0
    total = sum(vec.values())
    if total:
        for k in vec:
            vec[k] /= total
    return vec


def extract_code_references(content: str) -> list[str]:
    """Extract code-like references from markdown content."""
    # Simple heuristic: backtick references and function signatures
    refs = re.findall(r"`([^`]+)`", content)
    # Also find patterns like Module.function or file.py
    refs += re.findall(r"\b\w+\.\w+\b", content)
    return list(set(refs))


def extract_executable_blocks(content: str) -> list[str]:
    """Extract fenced code blocks from markdown."""
    pattern = r"```[\w]*\n(.*?)```"
    return re.findall(pattern, content, re.DOTALL)


def validate_block(block: str) -> bool:
    """Basic validation of a code block."""
    # Simple heuristic: non-empty and no obvious syntax error markers
    stripped = block.strip()
    if not stripped:
        return False
    # If it looks like a shell command, check for common errors
    if stripped.startswith(("$ ", "# ", "> ")):
        return True
    # Reject blocks with explicit error markers
    error_markers = ["SyntaxError", "Traceback", "ERROR", "Exception"]
    return not any(marker in stripped for marker in error_markers)


def extract_dependencies(content: str) -> list[str]:
    """Extract dependency names from documentation content."""
    # Look for package names in backticks or requirements style
    deps = re.findall(r"pip install ([\w\-]+)", content)
    deps += re.findall(r"import ([\w\.]+)", content)
    return list(set(deps))


def semver_distance(pinned: str, current: str) -> float:
    """Compute a simple semver distance between two version strings."""
    def parse(v: str) -> list[int]:
        return [int(x) for x in re.findall(r"\d+", v)[:3]]

    p = parse(pinned)
    c = parse(current)
    dist = 0.0
    for i, (a, b) in enumerate(zip(p, c)):
        dist += abs(a - b) / (10 ** i)
    return dist


def get_pinned_version(path: Path, dep: str) -> str | None:
    """Attempt to find a pinned version for a dependency."""
    # Look in requirements files or pyproject.toml near the doc
    for req_file in path.parent.glob("requirements*.txt"):
        text = req_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if dep.lower() in line.lower():
                m = re.search(r"==\s*([\d.]+)", line)
                if m:
                    return m.group(1)
    return None


def get_latest_version(dep: str) -> str | None:
    """Return a dummy latest version (no network)."""
    return "1.0.0"


def infer_audience(readability: float, jargon_density: float) -> str:
    """Infer intended audience from readability and jargon density."""
    if readability < 30 or jargon_density > 0.3:
        return "expert"
    if readability > 70 and jargon_density < 0.1:
        return "beginner"
    return "general"


def infer_department(path: Path) -> str:
    """Infer department from file path."""
    parts = path.parts
    for part in parts:
        lower = part.lower()
        if lower in ("docs", "doc", "documentation"):
            continue
        if lower in ("dev", "ops", "api", "frontend", "backend", "security", "qa"):
            return lower
    return "general"


def infer_topic(named_entities: list[str]) -> str:
    """Infer topic from named entities."""
    if not named_entities:
        return "general"
    return named_entities[0]


def infer_format(path: Path) -> str:
    """Infer document format from path."""
    return classify_doc_type(path)


def infer_expertise_level(concept_depth: float) -> str:
    """Infer expertise level from concept depth."""
    if concept_depth > 0.7:
        return "advanced"
    if concept_depth < 0.3:
        return "introductory"
    return "intermediate"


def edits_per_quarter(path: Path) -> float:
    """Estimate edits per quarter from file modification frequency."""
    if not path.exists():
        return 0.0
    stat = path.stat()
    age_days = (datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)).days
    if age_days <= 0:
        return 1.0
    # Heuristic: assume one edit per significant size block
    edits = max(1, stat.st_size // 500)
    quarters = max(1, age_days / 90)
    return edits / quarters


def avg_age_of_referenced_code(path: Path) -> float:
    """Return average age of referenced code files near the doc."""
    if not path.exists():
        return 0.0
    now = datetime.now(timezone.utc)
    ages = []
    for sibling in path.parent.iterdir():
        if sibling.suffix in (".py", ".js", ".ts", ".java", ".go", ".rs"):
            stat = sibling.stat()
            age = (now - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)).days
            ages.append(age)
    if not ages:
        return 0.0
    return sum(ages) / len(ages)
