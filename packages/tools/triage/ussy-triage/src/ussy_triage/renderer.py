"""Diagnosis Renderer — Produces detective-style diagnostic reports.

Multiple output formats:
- Detective report (default): Human-readable case summary with ASCII formatting
- JSON: Structured diagnosis for tool integration
- Minimal: Just the fix suggestion
- Teaching: Extended explanation for junior developers
"""

import json
from typing import List, Optional

from .models import Diagnosis, EnrichedError, Confidence, VictimType


# Unicode box drawing characters
BOLD_LINE = "━"
THIN_LINE = "─"
EM_DASH = "—"
MAGNIFY = "🔍"
SUSPECT_EMOJI = "🎯"
EVIDENCE_EMOJI = "📋"
MOTIVE_EMOJI = "💡"
WITNESS_EMOJI = "👁️"
ACTION_EMOJI = "🔧"
CASE_EMOJI = "📁"
TEACH_EMOJI = "📚"

# Teaching mode explanations for common error categories
TEACHING_NOTES = {
    "rust_compile": {
        "about": "Rust's compiler is one of the strictest. It catches errors at compile time that would crash at runtime in other languages.",
        "why_strict": "Rust enforces ownership rules, borrowing rules, and type safety at compile time. This prevents entire categories of runtime bugs (use-after-free, data races, null pointer dereference).",
        "common_mistakes": "The most common Rust beginner mistakes are: (1) Fighting the borrow checker — try cloning instead of borrowing, (2) Forgetting that `?` only works with compatible error types, (3) Not understanding that `String` and `&str` are different types.",
    },
    "python_error": {
        "about": "Python errors (exceptions) are raised at runtime. The traceback shows the call stack from the error back to the entry point.",
        "why_traceback": "Python tracebacks read bottom-to-top: the actual error is at the bottom, and each line above it shows who called that function.",
        "common_mistakes": "Common Python pitfalls: (1) Mutable default arguments (def f(x=[])), (2) Confusing `is` and `==`, (3) Forgetting that `except Exception as e` needs the `as e`, (4) Not handling file I/O in a `with` block.",
    },
    "typescript_compile": {
        "about": "TypeScript adds static types to JavaScript. The compiler checks types before the code runs, catching type errors early.",
        "why_types": "TypeScript's type system prevents runtime type errors. `any` bypasses the type checker — avoid it. Use `unknown` instead when you don't know the type.",
        "common_mistakes": "Common TypeScript issues: (1) Type assertion (`as`) doesn't change runtime behavior, (2) Missing type declarations for JS packages, (3) Not understanding that interfaces are structural (duck typing), not nominal.",
    },
    "go_compile": {
        "about": "Go's compiler enforces strict rules: unused imports, unused variables, and type safety.",
        "why_strict": "Go's philosophy is that compilation errors should catch real bugs. An unused import might mean you forgot to use a critical library.",
        "common_mistakes": "Common Go pitfalls: (1) Unexported names are private to the package (lowercase first letter), (2) Goroutine leaks from missing `defer close(ch)`, (3) Not closing HTTP response bodies.",
    },
    "js_runtime": {
        "about": "JavaScript runtime errors occur when the code is executing. Common causes include accessing properties on null/undefined and calling non-functions.",
        "why_loose": "JavaScript is dynamically typed — variables can hold any type at any time. This flexibility comes at the cost of runtime type errors.",
        "common_mistakes": "Common JS pitfalls: (1) `undefined` is not `null`, (2) Arrow functions don't have their own `this`, (3) `==` does type coercion, always use `===`, (4) Async functions need `await` or `.then()`.",
    },
    "cpp_compile": {
        "about": "C++ compilation errors can be notoriously long and cryptic. Template errors are especially verbose.",
        "why_verbose": "C++ templates are Turing-complete at compile time. When they fail, the error can include the entire template instantiation chain.",
        "common_mistakes": "Common C++ issues: (1) Undefined reference = declared but not defined (link the library!), (2) Header not found = missing include path, (3) Segfault = use sanitizers (`-fsanitize=address`).",
    },
    "test_failure": {
        "about": "Test failures mean your code doesn't meet its specification. The test is telling you what's wrong.",
        "why_important": "Failing tests are guardrails. They catch regressions before they reach production. Every failing test is a bug that didn't ship.",
        "common_mistakes": "Common testing pitfalls: (1) Tests that depend on execution order, (2) Hard-coded timestamps/paths, (3) Mocking too much or too little, (4) Not testing error paths.",
    },
}


class DiagnosisRenderer:
    """Renders diagnoses in multiple output formats."""

    def __init__(self, case_counter: int = 0):
        self.case_counter = case_counter

    def diagnose(self, enriched_error: EnrichedError) -> Diagnosis:
        """Create a full diagnosis from an enriched error."""
        self.case_counter += 1

        # Build suspect description
        suspect = self._build_suspect(enriched_error)

        # Gather evidence
        evidence = self._build_evidence(enriched_error)

        # Establish motive
        motive = self._build_motive(enriched_error)

        # Witness testimony
        witness = self._build_witness_testimony(enriched_error)

        # Recommended action
        action = self._build_recommended_action(enriched_error)

        # Confidence
        confidence, score = self._compute_confidence(enriched_error)

        return Diagnosis(
            case_number=self.case_counter,
            suspect=suspect,
            victim=enriched_error.victim_type,
            evidence=evidence,
            motive=motive,
            witness_testimony=witness,
            recommended_action=action,
            confidence=confidence,
            confidence_score=score,
            enriched_error=enriched_error,
        )

    def diagnose_all(self, errors: List[EnrichedError]) -> List[Diagnosis]:
        """Create diagnoses for all enriched errors."""
        return [self.diagnose(err) for err in errors]

    def render(self, diagnosis: Diagnosis, format: str = "detective") -> str:
        """Render a diagnosis in the specified format."""
        if format == "detective":
            return self._render_detective(diagnosis)
        elif format == "json":
            return self._render_json(diagnosis)
        elif format == "minimal":
            return self._render_minimal(diagnosis)
        elif format == "teaching":
            return self._render_teaching(diagnosis)
        else:
            return self._render_detective(diagnosis)

    def render_all(self, diagnoses: List[Diagnosis], format: str = "detective") -> str:
        """Render all diagnoses."""
        if not diagnoses:
            return f"{MAGNIFY} No errors found — the scene is clean."

        if format == "json":
            # JSON format must produce a single valid JSON array
            items = [self._render_json_dict(d) for d in diagnoses]
            return json.dumps(items, indent=2, default=str)

        parts = []
        for i, d in enumerate(diagnoses):
            if i > 0 and format == "detective":
                parts.append("\n" + THIN_LINE * 60 + "\n")
            parts.append(self.render(d, format))
        return "\n".join(parts)

    def _build_suspect(self, err: EnrichedError) -> str:
        """Build the suspect description."""
        parts = []

        if err.matched_pattern:
            parts.append(err.matched_pattern.root_cause)
        elif err.language:
            parts.append(f"{err.language.title()} error: {err.content.strip()[:100]}")
        else:
            parts.append(f"Error: {err.content.strip()[:100]}")

        if err.file_path:
            location = err.file_path
            if err.line_in_file:
                location += f":{err.line_in_file}"
            parts.append(f"Location: {location}")

        return "\n".join(parts)

    def _build_evidence(self, err: EnrichedError) -> List[str]:
        """Build the evidence list."""
        evidence = []

        # The error line itself
        evidence.append(f"Line {err.line_number}: {err.content.strip()}")

        # Context lines that seem relevant
        for ctx in err.context_before[-3:]:
            stripped = ctx.strip()
            if stripped:
                evidence.append(f"Context: {stripped}")

        for ctx in err.context_after[:3:]:
            stripped = ctx.strip()
            if stripped:
                evidence.append(f"Context: {stripped}")

        return evidence[:8]  # Limit evidence items

    def _build_motive(self, err: EnrichedError) -> str:
        """Build the motive (root cause hypothesis)."""
        if err.matched_pattern:
            return err.matched_pattern.root_cause

        # Fallback: generic motive based on error type
        motives = {
            "rust_compile": "A compilation error suggests a type mismatch, missing import, or incorrect usage of Rust's ownership system.",
            "go_compile": "A compilation error indicates an undefined name, type mismatch, or unused import.",
            "python_traceback": "A runtime exception was raised during execution. The traceback shows the call chain.",
            "python_error": "A Python exception occurred. Check the error type and message for details.",
            "typescript_compile": "A TypeScript type error — the code doesn't match the expected type definitions.",
            "js_runtime": "A JavaScript runtime error — attempting an operation on an unexpected value type.",
            "js_module": "A module resolution error — the specified module could not be found.",
            "cpp_compile": "A C/C++ compilation error — possibly a missing include, type mismatch, or syntax issue.",
            "cpp_linker": "A linker error — a symbol is declared but not defined. The implementation is missing.",
            "test_failure": "A test assertion failed — the actual output didn't match the expected output.",
            "oom": "The process ran out of available memory. This could be a memory leak or unexpectedly large data.",
            "segfault": "A segmentation fault — the program accessed invalid memory. Check for null pointers and buffer overflows.",
            "panic": "The program panicked — an unrecoverable condition was hit. Check the panic message.",
        }

        return motives.get(err.error_type,
            f"An error of type '{err.error_type}' occurred. The specific cause requires further investigation.")

    def _build_witness_testimony(self, err: EnrichedError) -> List[str]:
        """Build witness testimony from git history and context."""
        testimony = []

        # Git blame context
        if err.git_context:
            if err.git_context.author:
                testimony.append(
                    f"Last modified by {err.git_context.author}"
                    + (f" in commit {err.git_context.commit_hash[:7]}"
                       if err.git_context.commit_hash else "")
                )
            if err.git_context.commit_message:
                testimony.append(
                    f"Commit message: \"{err.git_context.commit_message}\""
                )
            if err.git_context.recent_commits:
                for commit in err.git_context.recent_commits[:3]:
                    testimony.append(
                        f"  → Recent change: {commit['hash'][:7]} — {commit['message']}"
                    )

        # History matches
        if err.history_matches:
            match_count = len(err.history_matches)
            testimony.append(
                f"This error pattern has appeared {match_count} time(s) in project history"
            )
            for match in err.history_matches[:2]:
                testimony.append(
                    f"  → Previous: {match.commit_hash[:7]} — {match.commit_message}"
                )

        return testimony

    def _build_recommended_action(self, err: EnrichedError) -> str:
        """Build the recommended action."""
        if err.matched_pattern:
            return err.matched_pattern.fix_template

        # Language-specific fallback advice
        fallbacks = {
            "rust": "Check the compiler error message carefully. Rust errors are usually very specific about what's wrong and suggest fixes.",
            "python": "Read the traceback from bottom to top. The bottom line is the error, each line above shows the call chain.",
            "go": "Go compiler errors are straightforward. Fix the first error first — subsequent errors may be cascading from it.",
            "typescript": "Check type definitions and imports. TypeScript errors often indicate a mismatch between what you have and what's expected.",
            "javascript": "Check for null/undefined values. Use optional chaining (?.) and nullish coalescing (??) for safer access.",
            "cpp": "Read the first error carefully. C++ template errors can produce long cascading messages — the first one is usually the root cause.",
            "java": "Check the exception type and message. Stack traces in Java show the exact line where the exception was thrown.",
        }

        return fallbacks.get(
            err.language,
            "Review the error message carefully. Check documentation for the error type."
        )

    def _compute_confidence(self, err: EnrichedError) -> tuple:
        """Compute diagnosis confidence level and score."""
        score = 0.3  # Base confidence

        # Boost for pattern match
        if err.matched_pattern:
            score = max(score, err.matched_pattern.confidence)

        # Boost for file path identification
        if err.file_path:
            score = min(score + 0.05, 1.0)

        # Boost for language detection
        if err.language:
            score = min(score + 0.03, 1.0)

        # Boost for git context
        if err.git_context:
            score = min(score + 0.05, 1.0)

        # Boost for history matches
        if err.history_matches:
            score = min(score + 0.05, 1.0)

        # Determine confidence level
        if score >= 0.8:
            level = Confidence.HIGH
        elif score >= 0.5:
            level = Confidence.MEDIUM
        else:
            level = Confidence.LOW

        return level, round(score, 2)

    # ─── RENDERERS ────────────────────────────────────────

    def _render_detective(self, d: Diagnosis) -> str:
        """Render a detective-style case report."""
        lines = []

        # Header
        lines.append(f"{MAGNIFY} CRIME SCENE: Error #{d.case_number}")
        lines.append("")
        lines.append(f"{BOLD_LINE * 3} {SUSPECT_EMOJI} THE SUSPECT {BOLD_LINE * 3}")
        lines.append(d.suspect)
        lines.append("")

        lines.append(f"{BOLD_LINE * 3} {EVIDENCE_EMOJI} THE EVIDENCE {BOLD_LINE * 3}")
        for item in d.evidence:
            lines.append(f"  {item}")
        lines.append("")

        lines.append(f"{BOLD_LINE * 3} {MOTIVE_EMOJI} THE MOTIVE {BOLD_LINE * 3}")
        lines.append(d.motive)
        lines.append("")

        if d.witness_testimony:
            lines.append(f"{BOLD_LINE * 3} {WITNESS_EMOJI} WITNESS TESTIMONY {BOLD_LINE * 3}")
            for item in d.witness_testimony:
                lines.append(f"  {EM_DASH} {item}")
            lines.append("")

        lines.append(f"{BOLD_LINE * 3} {ACTION_EMOJI} RECOMMENDED ACTION {BOLD_LINE * 3}")
        lines.append(d.recommended_action)
        lines.append("")

        # Case closed
        conf_emoji = "🟢" if d.confidence == Confidence.HIGH else "🟡" if d.confidence == Confidence.MEDIUM else "🔴"
        pattern_status = "known" if d.enriched_error and d.enriched_error.matched_pattern else "novel"
        severity = d.enriched_error.severity if d.enriched_error else "error"

        lines.append(f"{BOLD_LINE * 3} {CASE_EMOJI} CASE CLOSED? {BOLD_LINE * 3}")
        lines.append(
            f"{conf_emoji} Confidence: {int(d.confidence_score * 100)}% "
            f"| Pattern: {pattern_status} "
            f"| Severity: {severity}"
        )

        return "\n".join(lines)

    def _render_json(self, d: Diagnosis) -> str:
        """Render as structured JSON."""
        return json.dumps(self._render_json_dict(d), indent=2, ensure_ascii=False)

    def _render_json_dict(self, d: Diagnosis) -> dict:
        """Return diagnosis as a dict for JSON serialization."""
        return d.to_dict()

    def _render_minimal(self, d: Diagnosis) -> str:
        """Render minimal output — just the fix."""
        location = ""
        if d.enriched_error and d.enriched_error.file_path:
            location = f"[{d.enriched_error.file_path}"
            if d.enriched_error.line_in_file:
                location += f":{d.enriched_error.line_in_file}"
            location += "] "

        confidence_pct = int(d.confidence_score * 100)
        return f"{location}{d.recommended_action} (confidence: {confidence_pct}%)"

    def _render_teaching(self, d: Diagnosis) -> str:
        """Render with extended teaching explanations."""
        # Start with the detective report
        lines = [self._render_detective(d)]
        lines.append("")
        lines.append(f"{BOLD_LINE * 3} {TEACH_EMOJI} LEARN MORE {BOLD_LINE * 3}")

        # Add teaching notes based on error type
        err = d.enriched_error
        if err and err.error_type in TEACHING_NOTES:
            notes = TEACHING_NOTES[err.error_type]
            lines.append("")
            lines.append(f"What's happening: {notes['about']}")
            # Find the 'why' key (different notes use different key names)
            why_key = next((k for k in notes if k.startswith("why_")), None)
            if why_key:
                lines.append(f"Why it matters: {notes[why_key]}")
            lines.append(f"Common mistakes: {notes['common_mistakes']}")
        elif err and err.language and err.language in TEACHING_NOTES:
            notes = TEACHING_NOTES[err.language]
            lines.append("")
            lines.append(f"What's happening: {notes['about']}")
            why_key = next((k for k in notes if k.startswith("why_")), None)
            if why_key:
                lines.append(f"Why it matters: {notes[why_key]}")
            lines.append(f"Common mistakes: {notes['common_mistakes']}")
        else:
            lines.append("")
            lines.append("No teaching notes available for this error type.")
            lines.append("The recommended action above should help resolve the issue.")

        return "\n".join(lines)
