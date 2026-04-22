"""Contamination Tracker — Flaky Test Epidemiology.

Models flaky tests as biological contamination with spread dynamics.
Computes R0 (basic reproduction number), identifies patient zero,
and recommends quarantine and inoculation strategies.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ussy_calibre.models import (
    TestOutcomeLevain as TestOutcome,
    ContaminationNode,
    ContaminationReport,

    TestResult,
)


class ContaminationTracker:
    """Track flaky test contamination with epidemiological modeling."""

    def __init__(
        self,
        flaky_threshold: float = 0.3,
        min_runs: int = 3,
        shared_fixture_weight: float = 0.5,
        ordering_weight: float = 0.3,
        module_weight: float = 0.2,
    ):
        self.flaky_threshold = flaky_threshold
        self.min_runs = min_runs
        self.shared_fixture_weight = shared_fixture_weight
        self.ordering_weight = ordering_weight
        self.module_weight = module_weight

    def track(
        self,
        test_runs: list[list[TestResult]],
    ) -> ContaminationReport:
        """Analyze contamination from multiple test runs.

        Args:
            test_runs: List of test result lists, one per run.

        Returns:
            ContaminationReport with contamination map, R0, quarantine plan.
        """
        if not test_runs:
            return ContaminationReport(
                patient_zero=None,
                nodes=[],
                quarantine_plan=[],
                inoculation_suggestions=["No test data available"],
                overall_r0=0.0,
            )

        # Step 1: Identify flaky tests
        flaky_tests = self._identify_flaky(test_runs)

        if not flaky_tests:
            return ContaminationReport(
                patient_zero=None,
                nodes=[],
                quarantine_plan=[],
                inoculation_suggestions=["No flaky tests detected — culture is clean"],
                overall_r0=0.0,
            )

        # Step 2: Build contamination graph
        nodes = self._build_contamination_graph(test_runs, flaky_tests)

        # Step 3: Calculate R0 for each flaky test
        nodes = self._calculate_r0(nodes, test_runs)

        # Step 4: Find patient zero
        patient_zero = self._find_patient_zero(nodes)

        # Step 5: Generate quarantine plan
        quarantine_plan = self._generate_quarantine(nodes)

        # Step 6: Generate inoculation suggestions
        inoculation = self._generate_inoculation(nodes, test_runs)

        # Overall R0
        overall_r0 = (
            sum(n.r0 for n in nodes if n.is_flaky) / len([n for n in nodes if n.is_flaky])
            if any(n.is_flaky for n in nodes)
            else 0.0
        )

        return ContaminationReport(
            patient_zero=patient_zero,
            nodes=nodes,
            quarantine_plan=quarantine_plan,
            inoculation_suggestions=inoculation,
            overall_r0=overall_r0,
        )

    def _identify_flaky(self, test_runs: list[list[TestResult]]) -> dict[str, float]:
        """Identify flaky tests by measuring outcome variance across runs.

        Returns dict of test_id -> flakiness_score (0-1).
        """
        test_outcomes: dict[str, list[TestOutcome]] = defaultdict(list)

        for run in test_runs:
            for tr in run:
                test_outcomes[tr.test_id].append(tr.outcome)

        flaky = {}
        for test_id, outcomes in test_outcomes.items():
            if len(outcomes) < self.min_runs:
                continue

            # Flakiness = proportion of runs where outcome differs from the mode
            from collections import Counter
            outcome_counts = Counter(outcomes)
            mode_count = outcome_counts.most_common(1)[0][1]
            consistency = mode_count / len(outcomes)
            flakiness = 1.0 - consistency

            if flakiness >= self.flaky_threshold:
                flaky[test_id] = flakiness

        return flaky

    def _build_contamination_graph(
        self,
        test_runs: list[list[TestResult]],
        flaky_tests: dict[str, float],
    ) -> list[ContaminationNode]:
        """Build the contamination relationship graph."""
        # Gather all unique tests
        all_tests: dict[str, TestResult] = {}
        for run in test_runs:
            for tr in run:
                all_tests[tr.test_id] = tr

        # For each flaky test, find which tests it might infect
        # and which might infect it
        nodes = []
        for test_id, tr in all_tests.items():
            is_flaky = test_id in flaky_tests
            sources = []
            targets = []

            if is_flaky:
                # Check for shared fixtures (same module)
                for other_id, other_tr in all_tests.items():
                    if other_id == test_id:
                        continue
                    # Shared module = potential shared fixture
                    if other_tr.module == tr.module:
                        if other_id in flaky_tests:
                            sources.append(other_id)
                        targets.append(other_id)

            nodes.append(ContaminationNode(
                test_id=test_id,
                name=tr.name,
                module=tr.module,
                is_flaky=is_flaky,
                r0=0.0,
                infection_sources=sources,
                infected_targets=targets,
            ))

        return nodes

    def _calculate_r0(
        self,
        nodes: list[ContaminationNode],
        test_runs: list[list[TestResult]],
    ) -> list[ContaminationNode]:
        """Calculate R0 (basic reproduction number) for each flaky test.

        R0 = average number of other tests that become flaky after this one.
        Uses co-occurrence of failures across runs to estimate spread.
        """
        # Build test_id -> node lookup
        node_map = {n.test_id: n for n in nodes}

        # Track which tests fail in each run
        run_failures: list[set[str]] = []
        for run in test_runs:
            failures = {
                tr.test_id
                for tr in run
                if tr.outcome in (TestOutcome.FAILED, TestOutcome.ERROR)
            }
            run_failures.append(failures)

        # For each flaky test, estimate R0
        flaky_nodes = [n for n in nodes if n.is_flaky]

        for node in flaky_nodes:
            # Count runs where this test fails
            runs_where_flaky_fails = 0
            co_infected = defaultdict(int)

            for failures in run_failures:
                if node.test_id in failures:
                    runs_where_flaky_fails += 1
                    # Count other tests that also fail in the same run
                    for other_id in failures:
                        if other_id != node.test_id and other_id in node_map:
                            co_infected[other_id] += 1

            if runs_where_flaky_fails == 0:
                node.r0 = 0.0
                continue

            # R0: average number of co-failing tests per run where this test fails
            total_co_infections = sum(co_infected.values())
            r0 = total_co_infections / runs_where_flaky_fails

            # Scale by ordering and module weights
            # Tests in the same module that co-fail are more likely infected
            weighted_r0 = r0 * (self.shared_fixture_weight + self.module_weight)
            node.r0 = round(weighted_r0, 3)

        return nodes

    def _find_patient_zero(self, nodes: list[ContaminationNode]) -> Optional[str]:
        """Find the most likely patient zero (source of contamination).

        The test with the highest R0 and most infection sources is likely patient zero.
        """
        flaky_nodes = [n for n in nodes if n.is_flaky]
        if not flaky_nodes:
            return None

        # Sort by R0 descending, then by number of infection targets descending
        flaky_nodes.sort(key=lambda n: (n.r0, len(n.infected_targets)), reverse=True)
        return flaky_nodes[0].test_id

    def _generate_quarantine(self, nodes: list[ContaminationNode]) -> list[str]:
        """Generate quarantine plan — tests to isolate.

        Quarantine tests with R0 > 1.0 (superspreaders).
        """
        quarantine = []
        for node in nodes:
            if node.is_flaky and node.r0 > 1.0:
                quarantine.append(node.test_id)
            elif node.is_flaky and node.r0 > 0.5:
                quarantine.append(node.test_id)

        return quarantine

    def _generate_inoculation(
        self,
        nodes: list[ContaminationNode],
        test_runs: list[list[TestResult]],
    ) -> list[str]:
        """Generate inoculation suggestions to prevent future contamination."""
        suggestions = []

        # Find modules with multiple flaky tests
        module_flaky: dict[str, int] = defaultdict(int)
        for node in nodes:
            if node.is_flaky:
                module_flaky[node.module] += 1

        for module, count in module_flaky.items():
            if count >= 2:
                suggestions.append(
                    f"Module '{module}' has {count} flaky tests — consider fixture isolation "
                    "and independent test state reset"
                )

        # Check for ordering dependencies
        flaky_with_targets = [n for n in nodes if n.is_flaky and len(n.infected_targets) > 2]
        if flaky_with_targets:
            suggestions.append(
                "Some flaky tests infect many others — implement test ordering independence "
                "and state reset protocols between tests"
            )

        if not suggestions:
            suggestions.append(
                "Isolate flaky tests in separate CI runs to prevent contamination spread. "
                "Use fixture scoping and cleanup to minimize shared state."
            )

        return suggestions
