"""Governance prescription generation."""

from __future__ import annotations

from typing import Optional

from ussy_seral.models import (
    GovernancePrescription,
    GovernanceRule,
    ModuleMetrics,
    Stage,
)


# Built-in governance templates for each stage
BUILTIN_RULES: dict[Stage, dict] = {
    Stage.PIONEER: {
        "mandatory": [
            "At least 1 person must review code (can be author)",
            "No force-push to main branch",
        ],
        "recommended": [
            "Keep PRs small and fast (< 200 lines ideal)",
            "Use feature flags for experimental changes",
            "Document intent in PR description",
        ],
        "forbidden": [],
    },
    Stage.SERAL_EARLY: {
        "mandatory": [
            "Code review required (1 reviewer)",
            "CI must pass before merge",
            "No direct push to main",
        ],
        "recommended": [
            "New dependencies require justification comment",
            "Start adding unit tests for new code",
            "Document public APIs",
        ],
        "forbidden": [
            "Force-push to feature branches",
        ],
    },
    Stage.SERAL_MID: {
        "mandatory": [
            "Code review required (1 reviewer, minimum from module contributors)",
            "CI must pass before merge",
            "No direct push to main",
            "New dependencies require justification comment",
            "Max PR size: 400 lines",
        ],
        "recommended": [
            "Test requirement: 50% coverage for new code",
            "Document architectural decisions for new patterns",
            "Add integration tests for cross-module changes",
        ],
        "forbidden": [
            "Force-push to feature branches",
            "Experimental branch protection exemption",
        ],
    },
    Stage.SERAL_LATE: {
        "mandatory": [
            "2 reviewers required",
            "CI must pass before merge (including integration tests)",
            "No direct push to main",
            "New dependencies require ADR (Architecture Decision Record)",
            "Max PR size: 400 lines",
            "Breaking changes require team notification",
        ],
        "recommended": [
            "Test requirement: 70% coverage for new code",
            "Performance benchmarks for critical paths",
            "Security review for authentication-adjacent code",
        ],
        "forbidden": [
            "Force-push to any branch",
            "Skipping CI",
            "Adding TODO/FIXME without ticket",
        ],
    },
    Stage.CLIMAX: {
        "mandatory": [
            "2 reviewers required (min 1 from module owners)",
            "All changes need integration test coverage",
            "No new dependencies without ADR",
            "Breaking changes require RFC",
            "CI must pass on all dependent modules",
        ],
        "recommended": [
            "Canary deployment for all changes",
            "Performance regression testing",
            "Security review for auth-adjacent code",
        ],
        "forbidden": [
            "Direct push to main",
            "Skipping CI",
            "Adding TODO/FIXME without ticket",
            "Force-push to any branch",
        ],
    },
    Stage.DISTURBED: {
        "mandatory": [
            "1 reviewer required (focus on correctness)",
            "Document all changes in PR description",
            "Flag high-risk areas for extra attention",
        ],
        "recommended": [
            "Pair programming on critical changes",
            "Extra test coverage for refactored areas",
            "Communication to team about large changes",
            "Incremental changes preferred over big bang",
        ],
        "forbidden": [
            "Silent refactoring without PR",
            "Deleting code without migration plan",
        ],
    },
}


def get_builtin_rules(stage: Stage) -> dict:
    """Get the built-in governance rules for a stage as a dict."""
    return BUILTIN_RULES.get(stage, BUILTIN_RULES[Stage.PIONEER])


def prescribe(stage: Stage, path: str = "", metrics: Optional[ModuleMetrics] = None) -> GovernancePrescription:
    """Generate a governance prescription for a given stage."""
    rules = get_builtin_rules(stage)

    mandatory_rules = [
        GovernanceRule(category="mandatory", description=desc, stage=stage)
        for desc in rules.get("mandatory", [])
    ]
    recommended_rules = [
        GovernanceRule(category="recommended", description=desc, stage=stage)
        for desc in rules.get("recommended", [])
    ]
    forbidden_rules = [
        GovernanceRule(category="forbidden", description=desc, stage=stage)
        for desc in rules.get("forbidden", [])
    ]

    return GovernancePrescription(
        stage=stage,
        path=path,
        mandatory=mandatory_rules,
        recommended=recommended_rules,
        forbidden=forbidden_rules,
    )


def governance_diff(from_stage: Stage, to_stage: Stage) -> dict:
    """Compare governance rules between two stages.

    Returns a dict with 'added', 'removed', and 'changed' lists.
    """
    from_rules = get_builtin_rules(from_stage)
    to_rules = get_builtin_rules(to_stage)

    result: dict[str, list[str]] = {"added": [], "removed": [], "changed": []}

    for category in ("mandatory", "recommended", "forbidden"):
        from_set = set(from_rules.get(category, []))
        to_set = set(to_rules.get(category, []))

        added = to_set - from_set
        removed = from_set - to_set

        for item in sorted(added):
            result["added"].append(f"+ ADDED ({category}): {item}")
        for item in sorted(removed):
            result["removed"].append(f"- REMOVED ({category}): {item}")

    # Detect changes (rules that appear in both but with modifications)
    for category in ("mandatory", "recommended", "forbidden"):
        from_list = from_rules.get(category, [])
        to_list = to_rules.get(category, [])
        # Look for similar rules with slight modifications
        for fr in from_list:
            for tr in to_list:
                if fr != tr and _rules_are_related(fr, tr) and fr not in to_list and tr not in from_list:
                    result["changed"].append(f"~ CHANGED ({category}): {fr} → {tr}")

    return result


def _rules_are_related(rule_a: str, rule_b: str) -> bool:
    """Check if two rules are related (share significant words)."""
    words_a = set(rule_a.lower().split()) - {"a", "an", "the", "for", "to", "of", "in", "on", "with", "from", "by"}
    words_b = set(rule_b.lower().split()) - {"a", "an", "the", "for", "to", "of", "in", "on", "with", "from", "by"}
    if not words_a or not words_b:
        return False
    overlap = words_a & words_b
    return len(overlap) >= min(len(words_a), len(words_b)) * 0.4
