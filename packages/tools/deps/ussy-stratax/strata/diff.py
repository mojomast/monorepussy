"""Version diff comparison — compare behavioral profiles between versions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strata.models import DiffResult, ProbeResult, VersionProbeResult


class VersionDiffer:
    """Compare behavioral probe results between two versions of a package."""

    def diff(
        self,
        package: str,
        version_a: str,
        version_b: str,
        results_a: VersionProbeResult,
        results_b: VersionProbeResult,
    ) -> DiffResult:
        """Compare probe results between two versions."""
        # Build lookup: probe_name -> result
        results_map_a = {r.probe_name: r for r in results_a.results}
        results_map_b = {r.probe_name: r for r in results_b.results}

        behavioral_quakes = []
        new_behaviors = []
        removed_behaviors = []
        unchanged_count = 0

        all_probe_names = set(results_map_a.keys()) | set(results_map_b.keys())

        for probe_name in sorted(all_probe_names):
            in_a = probe_name in results_map_a
            in_b = probe_name in results_map_b

            if in_a and in_b:
                result_a = results_map_a[probe_name]
                result_b = results_map_b[probe_name]

                if result_a.passed != result_b.passed:
                    # Behavioral change!
                    if result_a.passed and not result_b.passed:
                        description = (
                            f"{probe_name}: passed in {version_a}, "
                            f"failed in {version_b}"
                        )
                    else:
                        description = (
                            f"{probe_name}: failed in {version_a}, "
                            f"passed in {version_b}"
                        )

                    behavioral_quakes.append({
                        "probe": probe_name,
                        "version_a_passed": result_a.passed,
                        "version_b_passed": result_b.passed,
                        "description": description,
                    })
                else:
                    unchanged_count += 1

            elif in_b and not in_a:
                new_behaviors.append(probe_name)
            elif in_a and not in_b:
                removed_behaviors.append(probe_name)

        return DiffResult(
            package=package,
            version_a=version_a,
            version_b=version_b,
            behavioral_quakes=behavioral_quakes,
            new_behaviors=new_behaviors,
            removed_behaviors=removed_behaviors,
            unchanged_count=unchanged_count,
        )

    def diff_from_history(
        self,
        package: str,
        version_a: str,
        version_b: str,
        version_history: List[VersionProbeResult],
    ) -> DiffResult:
        """Diff using a version history list, finding the two target versions."""
        result_a = None
        result_b = None

        for vr in version_history:
            if vr.version == version_a:
                result_a = vr
            if vr.version == version_b:
                result_b = vr

        if result_a is None:
            raise ValueError(f"Version {version_a} not found in history")
        if result_b is None:
            raise ValueError(f"Version {version_b} not found in history")

        return self.diff(package, version_a, version_b, result_a, result_b)
