"""Tests for endemic.report module."""

import pytest

from ussy_endemic.models import (
    DeveloperStats,
    HerdImmunityResult,
    Module,
    Pattern,
    PatternType,
    PatternStatus,
    PromoteResult,
    SIRSimulation,
    SIRState,
    TransmissionEvent,
    TransmissionTree,
    TransmissionVector,
    VaccinationStrategy,
    ZoonoticJump,
)
from ussy_endemic.report import (
    format_herd_immunity_report,
    format_promote_report,
    format_scan_report,
    format_simulation_report,
    format_trace_report,
)
from ussy_endemic.sir_model import simulate_sir


class TestFormatScanReport:
    def test_basic(self):
        patterns = [
            Pattern(name="bare-except", r0=3.2, status=PatternStatus.SPREADING,
                    prevalence_count=18, total_modules=47),
            Pattern(name="print-debugging", r0=0.6, status=PatternStatus.DYING,
                    prevalence_count=3, total_modules=47),
        ]
        report = format_scan_report(patterns, total_modules=47)
        assert "ENDEMIC" in report
        assert "bare-except" in report
        assert "SPREADING" in report

    def test_with_superspreaders(self):
        patterns = [
            Pattern(name="bare-except", r0=3.0, status=PatternStatus.SPREADING,
                    prevalence_count=10, total_modules=50),
        ]
        ss_modules = [("src/utils/helpers.py", 9)]
        ss_devs = [DeveloperStats(email="alice@test.com", infections_caused=6)]
        report = format_scan_report(
            patterns, total_modules=50,
            superspreader_modules=ss_modules,
            superspreader_devs=ss_devs,
        )
        assert "SUPERSPREADERS" in report
        assert "helpers.py" in report

    def test_critical_warning(self):
        patterns = [
            Pattern(name="bare-except", r0=3.2, pattern_type=PatternType.BAD,
                    status=PatternStatus.SPREADING,
                    prevalence_count=18, total_modules=47),
        ]
        report = format_scan_report(patterns, total_modules=47)
        assert "CRITICAL" in report

    def test_good_patterns(self):
        patterns = [
            Pattern(name="structured-logging", pattern_type=PatternType.GOOD,
                    r0=2.8, status=PatternStatus.SPREADING,
                    prevalence_count=22, total_modules=47),
        ]
        report = format_scan_report(patterns, total_modules=47)
        assert "✅" in report


class TestFormatTraceReport:
    def test_basic(self):
        tree = TransmissionTree(
            pattern_name="bare-except",
            index_case="soap_client.py",
            index_developer="bob@test.com",
        )
        tree.add_event(TransmissionEvent(
            pattern_name="bare-except",
            source_module="soap_client.py",
            target_module="xml_parser.py",
            vector=TransmissionVector.COPY_PASTE,
            developer="bob@test.com",
        ))
        report = format_trace_report(tree, r0=3.2)
        assert "Contact Tracing" in report
        assert "soap_client.py" in report
        assert "3.2" in report

    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        report = format_trace_report(tree, r0=0.0)
        assert "Contact Tracing" in report


class TestFormatHerdImmunityReport:
    def test_basic(self):
        result = HerdImmunityResult(
            pattern_name="bare-except", r0=3.2,
            threshold=0.688, current_immune_count=22,
            total_modules=47, modules_to_vaccinate=10,
        )
        report = format_herd_immunity_report(result)
        assert "Herd Immunity" in report
        assert "bare-except" in report

    def test_with_strategies(self):
        result = HerdImmunityResult(
            pattern_name="bare-except", r0=3.2,
            threshold=0.688, current_immune_count=22,
            total_modules=47, modules_to_vaccinate=10,
        )
        strategies = [
            VaccinationStrategy(
                target="Refactor helpers.py",
                action="Remove pattern",
                prevented_infections=9,
                effort_hours=2.0,
                rank=1,
            ),
        ]
        combined = {"combined_hours": 7.0, "full_refactor_hours": 35.0, "savings": 28.0}
        report = format_herd_immunity_report(result, strategies, combined)
        assert "Vaccination strategies" in report
        assert "helpers.py" in report


class TestFormatSimulationReport:
    def test_basic(self):
        sim = simulate_sir(
            n=47, initial_infected=5, initial_recovered=0,
            r0=3.0, gamma=0.1, horizon_steps=26,
        )
        report = format_simulation_report(sim, pattern_name="bare-except")
        assert "SIR Simulation" in report
        assert "bare-except" in report

    def test_with_intervention(self):
        from ussy_endemic.sir_model import simulate_with_intervention
        without, with_int = simulate_with_intervention(
            n=47, initial_infected=5, initial_recovered=0,
            r0=3.0, gamma=0.1,
            intervention_step=5,
            intervention_r0=0.5,
            horizon_steps=26,
        )
        report = format_simulation_report(without, "bare-except", with_intervention=with_int)
        assert "WITH intervention" in report


class TestFormatPromoteReport:
    def test_basic(self):
        result = PromoteResult(
            pattern_name="structured-logging",
            current_r0=2.8,
            current_prevalence=22,
            total_modules=47,
            optimal_seed_module="src/api/middleware.py",
            predicted_r0_increase=0.7,
            time_to_80pct_weeks=16,
            time_to_80pct_without_seeding_weeks=32,
        )
        report = format_promote_report(result)
        assert "Good Pathogen Promotion" in report
        assert "structured-logging" in report

    def test_with_cross_protection(self):
        result = PromoteResult(
            pattern_name="structured-logging",
            current_r0=2.8,
            cross_protection={"bare-except": 0.73},
        )
        report = format_promote_report(result)
        assert "Cross-protection" in report
        assert "73%" in report
