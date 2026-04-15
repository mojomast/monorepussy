"""Report formatting — display results in terminal-friendly format."""

from __future__ import annotations

from endemic.models import (
    DeveloperStats,
    HerdImmunityResult,
    Pattern,
    PatternType,
    PromoteResult,
    SIRSimulation,
    TransmissionTree,
    VaccinationStrategy,
    ZoonoticJump,
)
from endemic.sir_model import format_sir_chart


def format_scan_report(patterns: list[Pattern],
                       total_modules: int,
                       superspreader_modules: list[tuple[str, int]] = None,
                       superspreader_devs: list[DeveloperStats] = None,
                       superspreader_events: list[tuple] = None) -> str:
    """Format the main scan report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  ENDEMIC — Pattern Propagation Report")
    lines.append("=" * 70)
    lines.append("")

    # Count patterns
    total_patterns = len(patterns)
    spreading = sum(1 for p in patterns if p.is_spreading and p.pattern_type == PatternType.BAD)
    lines.append(f"  🔬 {total_patterns} propagating patterns detected")
    lines.append("")

    # Table header
    lines.append(f"  {'PATHOGEN':<40} {'R0':>5} {'STATUS':<10} {'PREVALENCE':<15}")
    lines.append(f"  {'─' * 40} {'─' * 5} {'─' * 10} {'─' * 15}")

    for p in sorted(patterns, key=lambda p: -p.r0):
        name = p.name
        if p.pattern_type == PatternType.GOOD:
            name = f"✅ {name} (good)"
        else:
            name = f"  {name}"

        prevalence = f"{p.prevalence_count}/{p.total_modules} modules"
        lines.append(f"  {name:<40} {p.r0:>5.1f} {p.status.value:<10} {prevalence:<15}")

    lines.append("")

    # Critical warnings
    critical = [p for p in patterns if p.r0 > 2.0 and p.pattern_type == PatternType.BAD]
    for p in critical:
        pct = p.prevalence_ratio * 100
        lines.append(f"  ⚠️  CRITICAL: \"{p.name}\" has R0={p.r0} and is in {pct:.0f}% of modules")
        from endemic.herd_immunity import herd_immunity_threshold
        hit = herd_immunity_threshold(p.r0)
        lines.append(f"     Herd immunity threshold: {hit * 100:.0f}% of modules need vaccination")

    lines.append("")

    # Superspreaders
    if superspreader_modules or superspreader_devs:
        lines.append("  🦠 SUPERSPREADERS:")
        if superspreader_modules:
            for mod, count in superspreader_modules[:3]:
                lines.append(f"     Module: {mod} (propagated to {count} modules)")
        if superspreader_devs:
            for dev in superspreader_devs[:3]:
                lines.append(f"     Developer: {dev.email} (introduced pattern in {dev.infection_count} modules)")
        if superspreader_events:
            for event, count in superspreader_events[:2]:
                pr_info = f"PR #{event.pr_number}" if event.pr_number else event.commit_hash[:8]
                lines.append(f"     Event: {pr_info} ({count} new infections)")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_trace_report(tree: TransmissionTree, r0: float = 0.0) -> str:
    """Format a contact tracing report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  ENDEMIC — Contact Tracing: {tree.pattern_name}")
    lines.append("=" * 70)
    lines.append("")

    if tree.index_case:
        date_str = tree.index_timestamp.strftime("%Y-%m-%d") if tree.index_timestamp else "unknown"
        lines.append(f"  Index case: {tree.index_case} ({date_str}, {tree.index_developer})")
        lines.append("")

    # Transmission tree (simplified ASCII)
    lines.append("  Transmission tree:")
    modules_by_source: dict[str, list[str]] = {}
    for event in tree.events:
        if event.source_module not in modules_by_source:
            modules_by_source[event.source_module] = []
        modules_by_source[event.source_module].append(event.target_module)

    for source, targets in modules_by_source.items():
        src_name = source.rsplit("/", 1)[-1] if "/" in source else source
        for i, target in enumerate(targets):
            tgt_name = target.rsplit("/", 1)[-1] if "/" in target else target
            prefix = "  ├──" if i < len(targets) - 1 else "  └──"
            if i == 0:
                lines.append(f"  {src_name} ─── {tgt_name}")
            else:
                lines.append(f"  {prefix} {tgt_name}")

    lines.append("")

    # Developer summary
    dev_counts: dict[str, int] = {}
    for event in tree.events:
        dev_counts[event.developer] = dev_counts.get(event.developer, 0) + 1

    for dev, count in sorted(dev_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {dev} ─── ({count} direct infections)")

    lines.append("")

    # Vector breakdown
    vector_counts = tree.vector_counts
    total = sum(vector_counts.values())
    if total > 0:
        lines.append("  Transmission vectors:")
        vector_labels = {
            "copy_paste": "Copy-paste within PR",
            "developer_habit": "Developer habit",
            "template_codegen": "Template/code-gen",
            "shared_module": "Shared module",
            "unknown": "Unknown/community",
        }
        for vtype, count in sorted(vector_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            label = vector_labels.get(vtype.value, vtype.value)
            marker = " ← Most common vector" if count == max(vector_counts.values()) else ""
            lines.append(f"    {label}: {count}/{total} ({pct:.0f}%){marker}")

    lines.append("")

    if tree.generation_time_weeks > 0:
        lines.append(f"  Generation time: ~{tree.generation_time_weeks:.1f} weeks")

    lines.append(f"  R0 = {r0:.1f}")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_herd_immunity_report(result: HerdImmunityResult,
                                strategies: list[VaccinationStrategy] = None,
                                combined: dict = None) -> str:
    """Format a herd immunity analysis report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  ENDEMIC — Herd Immunity Analysis")
    lines.append("=" * 70)
    lines.append("")

    lines.append(f"  Pattern: {result.pattern_name} (R0 = {result.r0})")
    lines.append("")

    lines.append(f"  Herd immunity threshold: 1 - 1/{result.r0:.1f} = {result.threshold_pct:.1f}%")
    lines.append(f"  Current immune modules: {result.current_immune_count}/{result.total_modules} ({result.current_immune_pct:.1f}%)")
    lines.append(f"  Modules to vaccinate: {result.modules_to_vaccinate} more (to reach {result.threshold_pct:.0f}%)")

    lines.append("")

    if strategies:
        lines.append("  Vaccination strategies (ranked by efficiency):")
        lines.append("")
        for s in strategies:
            lines.append(f"  {s.rank}. 🎯 {s.target}")
            lines.append(f"     → Prevents {s.prevented_infections} potential secondary infections")
            lines.append(f"     → Effort: ~{s.effort_hours:.0f} hours")
            lines.append(f"     → Impact: Equivalent to vaccinating {s.equivalent_random_vaccinations} random modules")
            lines.append("")

    if combined:
        lines.append(f"  Combined strategy achieves herd immunity in ~{combined['combined_hours']:.0f} hours of effort")
        lines.append(f"  vs. ~{combined['full_refactor_hours']:.0f} hours to refactor all infected modules individually")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_simulation_report(sim: SIRSimulation,
                             pattern_name: str = "",
                             with_intervention: SIRSimulation = None) -> str:
    """Format an SIR simulation report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  ENDEMIC — SIR Simulation: {pattern_name}")
    lines.append("=" * 70)
    lines.append("")

    lines.append("  WITHOUT intervention:")
    lines.append("")
    chart = format_sir_chart(sim)
    for line in chart.splitlines():
        lines.append(f"  {line}")
    lines.append("")

    if sim.peak_infected:
        lines.append(f"  Prediction: {sim.final_infected}/{sim.n} modules infected at end "
                      f"(peak: {sim.peak_infected} at step {sim.peak_time:.0f})")

    if with_intervention:
        lines.append("")
        lines.append("  WITH intervention:")
        lines.append("")
        chart2 = format_sir_chart(with_intervention)
        for line in chart2.splitlines():
            lines.append(f"  {line}")
        lines.append("")
        lines.append(
            f"  Prediction: {with_intervention.peak_infected}/{with_intervention.n} modules "
            f"infected at peak, declining after step {with_intervention.peak_time:.0f}"
        )
        eff_r0 = with_intervention.r0
        lines.append(f"  Effective R0 drops from {sim.r0:.1f} → {eff_r0:.1f}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_promote_report(result: PromoteResult) -> str:
    """Format a good pathogen promotion report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  ENDEMIC — Good Pathogen Promotion: {result.pattern_name}")
    lines.append("=" * 70)
    lines.append("")

    lines.append(f"  Current R0: {result.current_r0:.1f} (naturally spreading)")
    lines.append(f"  Current prevalence: {result.current_prevalence}/{result.total_modules} modules "
                  f"({result.current_prevalence / max(1, result.total_modules) * 100:.0f}%)")
    lines.append("")

    if result.optimal_seed_module:
        lines.append("  Optimal seeding strategy:")
        lines.append(f"  Seed {result.optimal_seed_module}")
        lines.append(f"  → Predicted increase in R0: {result.current_r0:.1f} → {result.current_r0 + result.predicted_r0_increase:.1f}")

        if result.time_to_80pct_weeks != float("inf"):
            lines.append(f"  → Time to 80% prevalence: {result.time_to_80pct_weeks:.0f} weeks", )
            if result.time_to_80pct_without_seeding_weeks != float("inf"):
                lines.append(
                    f"  (vs. {result.time_to_80pct_without_seeding_weeks:.0f} weeks without seeding)"
                )

    if result.cross_protection:
        lines.append("")
        lines.append("  Cross-protection:")
        for bad_name, prot in result.cross_protection.items():
            lines.append(f"  {result.pattern_name} provides {prot * 100:.0f}% protection against {bad_name}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
