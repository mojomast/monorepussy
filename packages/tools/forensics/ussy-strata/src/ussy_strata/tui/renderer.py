"""TUI renderer module — re-exports from tui package."""

from ussy_strata.tui import render_cross_section, render_legend, render_stratum_detail

__all__ = ["render_cross_section", "render_legend", "render_stratum_detail"]
