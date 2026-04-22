"""
Contour Map — ASCII contour map visualization of the pressure field.

Generates ASCII contour maps showing:
- Pressure head contours (where pressure is building)
- Flow vectors (direction and magnitude of data flow)
- Drawdown maps (impact of bottlenecks)
- Conductivity profiles (capacity map)

No external dependencies — pure ASCII art.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from .topology import Topology
from .grid import GridModel, solve_grid
from .darcy import FlowAnalysis, analyze_flow
from .drawdown import ConeOfDepression, compute_cone_of_depression


# ASCII contour levels
CONTOUR_CHARS = " .:-=+*#%@"
ARROW_CHARS = {
    (0, 1): "→",
    (0, -1): "←",
    (1, 0): "↓",
    (-1, 0): "↑",
    (1, 1): "↘",
    (1, -1): "↙",
    (-1, 1): "↗",
    (-1, -1): "↖",
}


def head_to_char(value: float, min_val: float, max_val: float) -> str:
    """Map a head value to an ASCII contour character."""
    if max_val <= min_val:
        return CONTOUR_CHARS[0]
    normalized = (value - min_val) / (max_val - min_val)
    idx = int(normalized * (len(CONTOUR_CHARS) - 1))
    idx = max(0, min(len(CONTOUR_CHARS) - 1, idx))
    return CONTOUR_CHARS[idx]


def flow_arrow(qx: float, qy: float) -> str:
    """Map flow vector to an arrow character."""
    mag = (qx**2 + qy**2) ** 0.5
    if mag < 1e-10:
        return "·"

    # Normalize
    nx_dir = qx / mag
    ny_dir = qy / mag

    # Quantize to 8 directions
    dx = round(nx_dir)
    dy = round(ny_dir)

    key = (dy, dx)
    return ARROW_CHARS.get(key, "·")


def generate_head_contour(grid: GridModel, width: int = 60, height: int = 20) -> str:
    """
    Generate an ASCII contour map of the hydraulic head field.

    Args:
        grid: Solved grid model
        width: Output width in characters
        height: Output height in characters

    Returns:
        ASCII art string of the head contour
    """
    if grid.head is None or np.all(grid.head == 0):
        return "(No head data available)"

    head = grid.head
    ny, nx = head.shape

    min_val = float(np.min(head))
    max_val = float(np.max(head))

    lines = []
    lines.append(f"Hydraulic Head Contour Map (h range: {min_val:.2f} - {max_val:.2f})")
    lines.append(f"Legend: {CONTOUR_CHARS} (low → high pressure)")
    lines.append("")

    # Sample grid to fit output size
    for row in range(height):
        j = int(row * (ny - 1) / max(height - 1, 1))
        line = ""
        for col in range(width):
            i = int(col * (nx - 1) / max(width - 1, 1))
            char = head_to_char(float(head[j, i]), min_val, max_val)
            line += char
        lines.append(line)

    # Add service labels
    lines.append("")
    label_line = "Services: "
    for name, svc in grid.topology.services.items():
        x_pos = int(svc.grid_x * (width - 1) / max(grid.nx - 1, 1))
        y_pos = int(svc.grid_y * (height - 1) / max(grid.ny - 1, 1))
        label_line += f"{name}({x_pos},{y_pos}) "
    lines.append(label_line)

    return "\n".join(lines)


def generate_flow_vector_map(grid: GridModel, width: int = 60, height: int = 20) -> str:
    """
    Generate an ASCII flow vector map showing direction of data flow.

    Args:
        grid: Solved grid model
        width: Output width in characters
        height: Output height in characters

    Returns:
        ASCII art string of the flow vectors
    """
    if grid.head is None or np.all(grid.head == 0):
        return "(No head data available)"

    qx, qy = grid.get_flow_vectors()
    ny, nx = qx.shape

    max_mag = float(np.max(np.sqrt(qx**2 + qy**2)))

    lines = []
    lines.append(f"Flow Vector Map (max magnitude: {max_mag:.2f} req/s)")
    lines.append("")

    for row in range(height):
        j = int(row * (ny - 1) / max(height - 1, 1))
        line = ""
        for col in range(width):
            i = int(col * (nx - 1) / max(width - 1, 1))
            arrow = flow_arrow(float(qx[j, i]), float(qy[j, i]))
            line += arrow
        lines.append(line)

    return "\n".join(lines)


def generate_drawdown_map(
    topology: Topology,
    degraded_service: str,
    time_seconds: float = 300.0,
    width: int = 60,
    height: int = 20,
) -> str:
    """
    Generate an ASCII drawdown map showing the cone of depression.

    Args:
        topology: The system topology
        degraded_service: The degraded service
        time_seconds: Time since degradation
        width: Output width
        height: Output height

    Returns:
        ASCII art string of the drawdown map
    """
    cone = compute_cone_of_depression(topology, degraded_service, 0.5, time_seconds)

    # Create a simple drawdown grid based on service positions
    max_dd = cone.max_drawdown if cone.max_drawdown > 0 else 1.0

    lines = []
    lines.append(f"Drawdown Map — Cone of Depression from {degraded_service}")
    lines.append(f"(time={time_seconds:.0f}s, max_drawdown={max_dd:.3f})")
    lines.append(f"Legend: {CONTOUR_CHARS} (no impact → heavy impact)")
    lines.append("")

    # Map services to drawdown
    dd_map: Dict[str, float] = {}
    for pt in cone.points:
        dd_map[pt.service_name] = pt.drawdown

    # Build grid
    ny = max(height, topology.grid_height + 2)
    nx = max(width // 2, topology.grid_width + 2)

    for row in range(ny):
        line = ""
        for col in range(nx):
            # Check if any service is at this position
            closest_dd = 0.0
            for name, svc in topology.services.items():
                if svc.grid_y == row and svc.grid_x == col:
                    closest_dd = max(closest_dd, dd_map.get(name, 0.0))
            char = head_to_char(closest_dd, 0, max_dd)
            line += char
        lines.append(line)

    lines.append("")
    lines.append("Impact summary:")
    for pt in sorted(cone.points, key=lambda p: -p.drawdown):
        if pt.drawdown > 0:
            lines.append(f"  {pt.service_name}: drawdown={pt.drawdown:.3f} ({pt.impact_percent:.1f}%)")

    return "\n".join(lines)


def generate_contour_report(topology: Topology, width: int = 60, height: int = 20) -> str:
    """
    Generate a complete contour report with head and flow maps.

    Args:
        topology: The system topology
        width: Map width
        height: Map height

    Returns:
        Complete ASCII report
    """
    grid = solve_grid(topology)
    analysis = analyze_flow(topology)

    sections = []
    sections.append("=" * 60)
    sections.append("AQUIFER — Groundwater Flow Contour Report")
    sections.append("=" * 60)
    sections.append("")

    sections.append(generate_head_contour(grid, width, height))
    sections.append("")
    sections.append(generate_flow_vector_map(grid, width, height))
    sections.append("")

    # Conductivity profile
    k_map = {name: svc.effective_K for name, svc in topology.services.items()}
    sections.append("Conductivity Profile (K = throughput capacity):")
    for name, K in sorted(k_map.items(), key=lambda x: -x[1]):
        bar_len = int(K / max(k_map.values()) * 40)
        bar = "█" * bar_len
        sections.append(f"  {name:15s} K={K:8.1f} {bar}")

    sections.append("")

    # Bottlenecks
    if analysis.bottlenecks:
        sections.append("⚠ Bottleneck Connections:")
        for b in analysis.bottlenecks:
            sections.append(
                f"  {b.source} → {b.target}: "
                f"q={b.flow_rate:.1f} (expected {b.expected_flow:.1f}), "
                f"severity={b.bottleneck_severity:.0%}"
            )
    else:
        sections.append("✓ No significant bottlenecks detected")

    return "\n".join(sections)
