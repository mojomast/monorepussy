"""Instrument 4: Relay Coordinator — Protection Coordination Across Layers.

Time-current characteristic: t_trip = TDS × (A/(I/I_pickup)^p - 1)
Coordination constraint: t_b(R_b) - t_p(R_p) ≥ CTI
Zone-based: Zone 1 (<80%, instantaneous), Zone 2 (<120%, delayed), Zone 3 (<200%, delayed)

Maps error handlers to relays, checks CTI constraints, identifies
blind spots and TCC overlaps.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.models import (
    CTIViolation,
    ErrorHandlerContext,
    HandlerZone,
    RelayReport,
)


class RelayCoordinator:
    """Protection coordination analysis for error handlers."""

    DEFAULT_CTI = 0.2  # seconds — Coordination Time Interval

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def analyze(self, cti_required: float = DEFAULT_CTI) -> RelayReport:
        """Run protection coordination analysis."""
        # Collect all error handlers from packages
        handlers = self._collect_handlers()

        # Check CTI violations between all pairs
        cti_violations = self._check_cti_violations(handlers, cti_required)

        # Map zone coverage
        zone_coverage = self._map_zone_coverage(handlers)

        # Find blind spots — packages with no error handler in any zone
        blind_spots = self._find_blind_spots(handlers)

        # Detect TCC overlaps
        tcc_overlaps = self._detect_tcc_overlaps(handlers)

        return RelayReport(
            handlers=handlers,
            cti_violations=cti_violations,
            zone_coverage=zone_coverage,
            blind_spots=blind_spots,
            tcc_overlaps=tcc_overlaps,
        )

    def _collect_handlers(self) -> List[ErrorHandlerContext]:
        """Collect error handler metadata from all packages."""
        handlers: List[ErrorHandlerContext] = []

        for pkg_name, pkg in self.graph.packages.items():
            if pkg.has_error_handler:
                # Determine zone based on dependency depth
                zone = self._determine_zone(pkg_name)
                handlers.append(ErrorHandlerContext(
                    package=pkg_name,
                    zone=zone,
                    timeout_ms=pkg.handler_timeout_ms,
                    retry_count=pkg.handler_retry_count,
                    tds=pkg.handler_tds,
                    pickup=pkg.handler_pickup,
                ))

        return handlers

    def _determine_zone(self, package: str) -> HandlerZone:
        """Determine protection zone based on position in dependency graph.

        Zone 1: Leaf packages (no dependencies of their own) — immediate
        Zone 2: Mid-level packages — backup
        Zone 3: Top-level / root packages — remote
        """
        deps = self.graph.dependencies(package)
        dependents = self.graph.dependents(package)

        if not deps and dependents:
            # Leaf node with consumers
            return HandlerZone.ZONE_1
        elif deps and dependents:
            # Mid-level
            return HandlerZone.ZONE_2
        else:
            # Root or isolated
            return HandlerZone.ZONE_3

    def _check_cti_violations(
        self,
        handlers: List[ErrorHandlerContext],
        cti_required: float,
    ) -> List[CTIViolation]:
        """Check coordination time interval violations between handler pairs."""
        violations: List[CTIViolation] = []

        # Compare handlers in different zones
        # Primary is always the lower zone number
        for i, h1 in enumerate(handlers):
            for h2 in handlers[i + 1:]:
                # Determine primary/backup based on zone
                if h1.zone.value < h2.zone.value:
                    primary, backup = h1, h2
                elif h2.zone.value < h1.zone.value:
                    primary, backup = h2, h1
                else:
                    # Same zone — compare by TDS (lower = faster)
                    if h1.tds <= h2.tds:
                        primary, backup = h1, h2
                    else:
                        primary, backup = h2, h1

                # Calculate trip times at a typical fault current
                fault_current = 5.0  # typical fault
                t_primary = primary.trip_time(fault_current)
                t_backup = backup.trip_time(fault_current)

                if t_primary != float("inf") and t_backup != float("inf"):
                    violation = CTIViolation(
                        primary_handler=primary.package,
                        backup_handler=backup.package,
                        primary_trip_time=t_primary,
                        backup_trip_time=t_backup,
                        cti_required=cti_required,
                    )
                    if violation.violation_severity != "none":
                        violations.append(violation)

        return violations

    def _map_zone_coverage(
        self, handlers: List[ErrorHandlerContext]
    ) -> Dict[str, List[str]]:
        """Map which packages are covered by which protection zone."""
        coverage: Dict[str, List[str]] = {
            "zone_1": [],
            "zone_2": [],
            "zone_3": [],
        }

        for handler in handlers:
            zone_key = handler.zone.value
            if zone_key not in coverage:
                coverage[zone_key] = []
            coverage[zone_key].append(handler.package)

        # Packages in dependency chains covered by each handler
        for handler in handlers:
            transitive = self.graph.transitive_dependents(handler.package)
            zone_key = handler.zone.value
            for dep in transitive:
                if dep not in coverage[zone_key]:
                    coverage[zone_key].append(dep)

        return coverage

    def _find_blind_spots(self, handlers: List[ErrorHandlerContext]) -> List[str]:
        """Find packages with no error handler coverage in any zone."""
        covered: Set[str] = set()
        for handler in handlers:
            covered.add(handler.package)
            covered.update(self.graph.transitive_dependents(handler.package))

        all_packages = set(self.graph.packages.keys())
        blind = sorted(all_packages - covered)
        return blind

    def _detect_tcc_overlaps(
        self, handlers: List[ErrorHandlerContext]
    ) -> List[Tuple[str, str]]:
        """Detect overlapping time-current characteristics.

        Two handlers overlap if their trip times at the same fault current
        are within 10% of each other — they'll collide on retry schedules.
        """
        overlaps: List[Tuple[str, str]] = []

        for i, h1 in enumerate(handlers):
            for h2 in handlers[i + 1:]:
                # Check trip times across a range of fault currents
                has_overlap = False
                for fault_current in [2.0, 5.0, 10.0, 20.0]:
                    t1 = h1.trip_time(fault_current)
                    t2 = h2.trip_time(fault_current)
                    if t1 == float("inf") or t2 == float("inf"):
                        continue
                    if t1 > 0 and t2 > 0:
                        ratio = min(t1, t2) / max(t1, t2)
                        if ratio > 0.9:  # within 10%
                            has_overlap = True
                            break

                if has_overlap:
                    overlaps.append((h1.package, h2.package))

        return overlaps
