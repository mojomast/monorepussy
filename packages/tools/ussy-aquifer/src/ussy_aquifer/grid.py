"""
Finite Difference Grid — 2D pressure field solver.

Builds a finite difference grid model of the infrastructure and solves
the groundwater flow equation using iterative methods (Gauss-Seidel).

Steady-state: ∂²h/∂x² + ∂²h/∂y² = 0  (Laplace equation)
With variable K: ∂/∂x(K ∂h/∂x) + ∂/∂y(K ∂h/∂y) = 0

Uses numpy for the 2D grid computations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .topology import ServiceLayer, Topology


@dataclass
class GridModel:
    """
    Finite difference grid model of the infrastructure.

    Each grid cell represents a unit of the system. Service locations
    are marked on the grid with their K and h values. The solver
    computes the steady-state head distribution.
    """

    topology: Topology
    nx: int = 0  # Grid width
    ny: int = 0  # Grid height
    K: Optional[np.ndarray] = None  # Hydraulic conductivity field
    head: Optional[np.ndarray] = None  # Hydraulic head field
    S: Optional[np.ndarray] = None  # Storage coefficient field
    service_mask: Optional[np.ndarray] = None  # Boolean mask of service locations
    converged: bool = False
    iterations: int = 0
    residual: float = 0.0

    def __post_init__(self) -> None:
        if self.nx == 0 or self.ny == 0:
            self.nx = max(5, self.topology.grid_width + 2)
            self.ny = max(5, self.topology.grid_height + 2)
        self._initialize_fields()

    def _initialize_fields(self) -> None:
        """Initialize grid fields from topology."""
        self.K = np.ones((self.ny, self.nx)) * 1.0  # Default K=1
        self.head = np.zeros((self.ny, self.nx))
        self.S = np.ones((self.ny, self.nx)) * 0.01
        self.service_mask = np.zeros((self.ny, self.nx), dtype=bool)

        for name, svc in self.topology.services.items():
            x, y = svc.grid_x, svc.grid_y
            if 0 <= x < self.nx and 0 <= y < self.ny:
                self.K[y, x] = svc.effective_K
                self.head[y, x] = svc.hydraulic_head
                self.S[y, x] = svc.specific_storage
                self.service_mask[y, x] = True

        # For non-service cells, interpolate K from neighbors
        self._interpolate_K()

    def _interpolate_K(self) -> None:
        """Interpolate K values for non-service cells using inverse distance."""
        if self.K is None:
            return
        service_positions = []
        for name, svc in self.topology.services.items():
            service_positions.append((svc.grid_x, svc.grid_y, svc.effective_K))

        if not service_positions:
            return

        for j in range(self.ny):
            for i in range(self.nx):
                if not self.service_mask[j, i]:
                    total_weight = 0.0
                    weighted_K = 0.0
                    for sx, sy, sK in service_positions:
                        dist = max(0.1, ((i - sx) ** 2 + (j - sy) ** 2) ** 0.5)
                        weight = 1.0 / (dist**2)
                        weighted_K += weight * sK
                        total_weight += weight
                    if total_weight > 0:
                        self.K[j, i] = weighted_K / total_weight

    def solve(self, max_iterations: int = 5000, tolerance: float = 1e-6) -> "GridModel":
        """
        Solve for steady-state head distribution using Gauss-Seidel iteration.

        For variable K, the discretized equation is:
        K_{i+1/2}(h_{i+1}-h_i) - K_{i-1/2}(h_i-h_{i-1}) +
        K_{j+1/2}(h_{j+1}-h_j) - K_{j-1/2}(h_j-h_{j-1}) = 0

        Which gives:
        h_{i,j} = [K_e*h_{i+1,j} + K_w*h_{i-1,j} + K_n*h_{i,j+1} + K_s*h_{i,j-1}] /
                  [K_e + K_w + K_n + K_s]

        Where K_e, K_w, K_n, K_s are harmonic means of K at cell interfaces.
        """
        if self.head is None or self.K is None:
            return self

        h = self.head.copy()
        K = self.K

        for iteration in range(max_iterations):
            max_change = 0.0
            for j in range(1, self.ny - 1):
                for i in range(1, self.nx - 1):
                    if self.service_mask[j, i]:
                        continue  # Fixed head at service locations

                    # Harmonic mean K at interfaces
                    K_e = 2 * K[j, i] * K[j, i + 1] / (K[j, i] + K[j, i + 1]) if (K[j, i] + K[j, i + 1]) > 0 else 0
                    K_w = 2 * K[j, i] * K[j, i - 1] / (K[j, i] + K[j, i - 1]) if (K[j, i] + K[j, i - 1]) > 0 else 0
                    K_n = 2 * K[j, i] * K[j + 1, i] / (K[j, i] + K[j + 1, i]) if (K[j, i] + K[j + 1, i]) > 0 else 0
                    K_s = 2 * K[j, i] * K[j - 1, i] / (K[j, i] + K[j - 1, i]) if (K[j, i] + K[j - 1, i]) > 0 else 0

                    denom = K_e + K_w + K_n + K_s
                    if denom <= 0:
                        continue

                    h_new = (K_e * h[j, i + 1] + K_w * h[j, i - 1] +
                             K_n * h[j + 1, i] + K_s * h[j - 1, i]) / denom

                    change = abs(h_new - h[j, i])
                    if change > max_change:
                        max_change = change
                    h[j, i] = h_new

            if max_change < tolerance:
                self.converged = True
                self.iterations = iteration + 1
                break
        else:
            self.iterations = max_iterations

        self.head = h
        self.residual = max_change if 'max_change' in dir() else 0.0
        return self

    def get_flow_vectors(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute flow vectors (Darcy velocity) from the head field.

        q_x = -K * dh/dx
        q_y = -K * dh/dy

        Returns:
            (qx, qy) — flow components in x and y directions
        """
        if self.head is None or self.K is None:
            return np.zeros((self.ny, self.nx)), np.zeros((self.ny, self.nx))

        # Compute gradients using central differences
        dh_dx = np.zeros_like(self.head)
        dh_dy = np.zeros_like(self.head)

        # Central differences for interior
        dh_dx[:, 1:-1] = (self.head[:, 2:] - self.head[:, :-2]) / 2.0
        if self.ny > 2:
            dh_dy[1:-1, :] = (self.head[2:, :] - self.head[:-2, :]) / 2.0

        # Forward/backward at boundaries
        if self.nx > 1:
            dh_dx[:, 0] = self.head[:, 1] - self.head[:, 0]
            dh_dx[:, -1] = self.head[:, -1] - self.head[:, -2]
        if self.ny > 1:
            dh_dy[0, :] = self.head[1, :] - self.head[0, :]
            dh_dy[-1, :] = self.head[-1, :] - self.head[-2, :]

        # Fix dh_dy for non-square arrays
        if self.ny > 2:
            dh_dy[1:-1, :] = (self.head[2:, :] - self.head[:-2, :]) / 2.0

        qx = -self.K * dh_dx
        qy = -self.K * dh_dy

        return qx, qy

    def get_head_at(self, x: int, y: int) -> float:
        """Get hydraulic head at grid position."""
        if self.head is None:
            return 0.0
        if 0 <= x < self.nx and 0 <= y < self.ny:
            return float(self.head[y, x])
        return 0.0

    def get_K_at(self, x: int, y: int) -> float:
        """Get hydraulic conductivity at grid position."""
        if self.K is None:
            return 0.0
        if 0 <= x < self.nx and 0 <= y < self.ny:
            return float(self.K[y, x])
        return 0.0


def build_grid(topology: Topology, nx: Optional[int] = None, ny: Optional[int] = None) -> GridModel:
    """
    Build a finite difference grid from a topology.

    Args:
        topology: The system topology
        nx: Grid width (auto-calculated if None)
        ny: Grid height (auto-calculated if None)

    Returns:
        Initialized (but not yet solved) GridModel
    """
    model = GridModel(topology=topology)
    if nx is not None:
        model.nx = nx
    if ny is not None:
        model.ny = ny
    if nx is not None or ny is not None:
        model._initialize_fields()
    return model


def solve_grid(topology: Topology, max_iterations: int = 5000, tolerance: float = 1e-6) -> GridModel:
    """
    Build and solve a finite difference grid for the given topology.

    Returns:
        Solved GridModel with converged head distribution
    """
    model = build_grid(topology)
    model.solve(max_iterations=max_iterations, tolerance=tolerance)
    return model
