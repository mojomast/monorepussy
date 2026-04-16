"""Distribution model — change reach and volume of distribution."""

import math
from dataclasses import dataclass
from typing import Dict, List, Set

from dosemate.dependency_graph import DependencyGraphAnalyzer, ModuleInfo
from dosemate.git_parser import CommitInfo


@dataclass
class DistributionParams:
    """Distribution parameters for a change."""
    Vd: float  # Volume of distribution (modules)
    Kp: float  # Tissue partition coefficient (change amplification)
    fu: float  # Unbound fraction (public API fraction, 0-1)
    total_dependent_modules: int  # Number of dependent modules
    central_compartment_size: int  # Directly modified modules
    peripheral_compartment_size: int  # Downstream dependent modules

    def effective_concentration(self, dose_lines: int) -> float:
        """Compute effective change concentration per module.

        C = dose * fu / Vd
        """
        if self.Vd <= 0:
            return 0.0
        return dose_lines * self.fu / self.Vd


def compute_distribution(
    changed_files: List[str],
    dep_analyzer: DependencyGraphAnalyzer,
    file_to_module: Dict[str, str],
) -> DistributionParams:
    """Compute distribution parameters for a set of changed files.

    Args:
        changed_files: List of file paths that changed
        dep_analyzer: Dependency graph analyzer (already analyzed)
        file_to_module: Mapping of file paths to module names

    Returns:
        DistributionParams with computed values
    """
    modules = dep_analyzer.modules

    # Identify directly modified modules (central compartment)
    central_modules: Set[str] = set()
    for f in changed_files:
        mod = file_to_module.get(f, "root")
        central_modules.add(mod)

    # Identify all affected modules including dependents (peripheral compartment)
    peripheral_modules: Set[str] = set()
    for mod in central_modules:
        dependents = dep_analyzer.get_dependent_modules(mod)
        peripheral_modules.update(dependents)

    # Remove central from peripheral
    peripheral_modules -= central_modules

    total_affected = len(central_modules) + len(peripheral_modules)

    # Volume of distribution
    # Vd = total_dependent_modules / (lines_changed / total_files_in_module)
    # Simplified: Vd = total_affected_modules / max(central_modules, 1)
    # Scale so typical changes produce reasonable Vd (5-50 range)
    if central_modules:
        lines_per_module = len(changed_files) / len(central_modules)
        Vd = total_affected / max(lines_per_module, 0.5)
    else:
        Vd = float(total_affected) if total_affected > 0 else 1.0

    # Ensure Vd is at least 1
    Vd = max(Vd, 1.0)

    # Tissue partition coefficient Kp
    # Kp > 1: change amplifies in dependents
    # Kp < 1: change dampens in dependents
    if central_modules:
        # Count changes in central vs peripheral
        central_change_density = len(changed_files) / max(len(central_modules), 1)
        # Estimate peripheral change density from coupling
        peripheral_coupling = 0.0
        for mod in central_modules:
            if mod in modules:
                for dep in modules[mod].imported_by:
                    peripheral_coupling += dep_analyzer.compute_coupling(mod, dep)
        peripheral_coupling = peripheral_coupling / max(len(peripheral_modules), 1) if peripheral_modules else 0.5
        Kp = max(peripheral_coupling * 2, 0.1)
    else:
        Kp = 1.0

    # Unbound fraction: fraction of change visible through public APIs
    fu_values = []
    for mod in central_modules:
        fu_values.append(dep_analyzer.get_public_api_fraction(mod))
    fu = sum(fu_values) / len(fu_values) if fu_values else 0.5

    return DistributionParams(
        Vd=Vd,
        Kp=Kp,
        fu=fu,
        total_dependent_modules=total_affected,
        central_compartment_size=len(central_modules),
        peripheral_compartment_size=len(peripheral_modules),
    )
