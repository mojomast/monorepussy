"""Data models for Assay analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Category(str, Enum):
    """Code classification categories — the 'elements' of ore."""

    BUSINESS = "business"
    VALIDATION = "validation"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    FRAMEWORK = "framework"
    SLAG = "slag"
    UNKNOWN = "unknown"

    @property
    def icon(self) -> str:
        icons = {
            Category.BUSINESS: "\U0001f48e",       # 💎
            Category.VALIDATION: "\U0001f6e1\ufe0f", # 🛡️
            Category.ERROR_HANDLING: "\u26a0\ufe0f", # ⚠️
            Category.LOGGING: "\U0001f4dd",          # 📝
            Category.FRAMEWORK: "\U0001f50c",        # 🔌
            Category.SLAG: "\U0001f5d1\ufe0f",       # 🗑️
            Category.UNKNOWN: "\u2753",               # ❓
        }
        return icons.get(self, "?")

    @property
    def display_name(self) -> str:
        names = {
            Category.BUSINESS: "Business",
            Category.VALIDATION: "Validation",
            Category.ERROR_HANDLING: "Error Handling",
            Category.LOGGING: "Logging",
            Category.FRAMEWORK: "Framework",
            Category.SLAG: "Slag",
            Category.UNKNOWN: "Unknown",
        }
        return names.get(self, "Unknown")


@dataclass
class ClassifiedLine:
    """A single line of code with its classification."""

    line_number: int
    content: str
    category: Category
    is_comment: bool = False


@dataclass
class FunctionAnalysis:
    """Analysis result for a single function/method."""

    name: str
    file_path: str
    start_line: int
    end_line: int
    lines: list[ClassifiedLine] = field(default_factory=list)
    grade: float = 0.0
    category_counts: dict[str, int] = field(default_factory=dict)
    total_lines: int = 0
    business_lines: int = 0

    def __post_init__(self) -> None:
        self.total_lines = max(len(self.lines), self.end_line - self.start_line + 1)
        self.business_lines = sum(
            1 for ln in self.lines if ln.category == Category.BUSINESS
        )
        # Only recalculate category_counts and grade from lines if we have lines
        if self.lines:
            self.category_counts = {}
            for ln in self.lines:
                key = ln.category.value
                self.category_counts[key] = self.category_counts.get(key, 0) + 1
            if self.total_lines > 0:
                self.grade = round(self.business_lines / self.total_lines * 100, 1)
            else:
                self.grade = 0.0

    @property
    def slag_lines(self) -> int:
        return self.category_counts.get(Category.SLAG.value, 0)

    @property
    def concern_count(self) -> int:
        """Number of distinct non-unknown, non-slag categories present."""
        return sum(
            1
            for cat, cnt in self.category_counts.items()
            if cnt > 0 and cat not in (Category.UNKNOWN.value, Category.SLAG.value)
        )


@dataclass
class ModuleAnalysis:
    """Analysis result for a single file/module."""

    file_path: str
    functions: list[FunctionAnalysis] = field(default_factory=list)
    grade: float = 0.0
    total_lines: int = 0
    business_lines: int = 0

    def __post_init__(self) -> None:
        self.total_lines = sum(f.total_lines for f in self.functions)
        self.business_lines = sum(f.business_lines for f in self.functions)
        if self.total_lines > 0:
            self.grade = round(self.business_lines / self.total_lines * 100, 1)
        else:
            self.grade = 0.0


@dataclass
class AlloyInfo:
    """Information about an alloyed (mixed-concern) function."""

    function: FunctionAnalysis
    concern_count: int = 0
    interleaving_count: int = 0
    concerns_present: list[Category] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    projected_grade: float = 0.0

    def __post_init__(self) -> None:
        if self.concern_count == 0:
            self.concern_count = self.function.concern_count
        if not self.concerns_present:
            self.concerns_present = [
                Category(cat)
                for cat, cnt in self.function.category_counts.items()
                if cnt > 0 and cat != Category.UNKNOWN.value
            ]
        # Project grade if top non-business concern is extracted
        if self.function.total_lines > 0 and self.concern_count > 1:
            non_biz = {
                cat: cnt
                for cat, cnt in self.function.category_counts.items()
                if cat != Category.BUSINESS.value and cat != Category.UNKNOWN.value
            }
            if non_biz:
                biggest_non_biz = max(non_biz.values())
                new_total = max(1, self.function.total_lines - biggest_non_biz)
                self.projected_grade = round(
                    self.function.business_lines / new_total * 100, 1
                )
            else:
                self.projected_grade = self.function.grade
        else:
            self.projected_grade = self.function.grade


@dataclass
class SlagItem:
    """A single detected piece of slag."""

    file_path: str
    line_number: int
    content: str
    slag_type: str  # "debug_log", "todo_comment", "unreachable_branch", "commented_out"


@dataclass
class SlagReport:
    """Full slag inventory for a codebase."""

    items: list[SlagItem] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return len(self.items)

    @property
    def files_affected(self) -> int:
        return len({item.file_path for item in self.items})

    @property
    def by_type(self) -> dict[str, list[SlagItem]]:
        result: dict[str, list[SlagItem]] = {}
        for item in self.items:
            result.setdefault(item.slag_type, []).append(item)
        return result


@dataclass
class CrucibleEntry:
    """Entry in the crucible map — a function ranked by value."""

    function: FunctionAnalysis
    caller_count: int = 0
    value_score: float = 0.0

    def __post_init__(self) -> None:
        if self.value_score == 0.0:
            # Value score = grade * (caller_count + 1) — unweighted base
            self.value_score = round(self.function.grade * (self.caller_count + 1), 1)


@dataclass
class GradeTrend:
    """Trend information for a function's grade over time."""

    function_name: str
    current_grade: float
    previous_grade: float = 0.0
    delta: float = 0.0

    def __post_init__(self) -> None:
        self.delta = round(self.current_grade - self.previous_grade, 1)

    @property
    def trend_symbol(self) -> str:
        if self.delta > 0:
            return "\u25b2"  # ▲
        elif self.delta < 0:
            return "\u25bc"  # ▼
        return "\u2500"  # ─


@dataclass
class ProjectAnalysis:
    """Full analysis for a project / directory."""

    modules: list[ModuleAnalysis] = field(default_factory=list)
    grade: float = 0.0
    total_lines: int = 0
    business_lines: int = 0

    def __post_init__(self) -> None:
        self.total_lines = sum(m.total_lines for m in self.modules)
        self.business_lines = sum(m.business_lines for m in self.modules)
        if self.total_lines > 0:
            self.grade = round(self.business_lines / self.total_lines * 100, 1)
        else:
            self.grade = 0.0

    @property
    def all_functions(self) -> list[FunctionAnalysis]:
        result: list[FunctionAnalysis] = []
        for mod in self.modules:
            result.extend(mod.functions)
        return result
