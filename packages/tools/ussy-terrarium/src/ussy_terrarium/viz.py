"""Rich-based visualization dashboard for Terrarium health scores."""

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .health import HealthScore


def render_dashboard(health: HealthScore) -> str:
    """Render a Rich dashboard showing organism health as an ASCII ecosystem.

    Args:
        health: A HealthScore with sub-scores for each ussyverse source.

    Returns:
        A Rich-renderable string (use Console().print() to display).
    """
    # Overall health bar
    overall_color = _score_color(health.overall)
    overall_bar = _bar(health.overall)

    table = Table(
        title="🌿 Terrarium Ecosystem Dashboard",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Bar", min_width=20)
    table.add_column("Status", justify="center")

    dimensions = [
        ("Overall", health.overall),
        ("Fatigue", health.fatigue),
        ("Epidemic", health.epidemic),
        ("Anomaly", health.anomaly),
        ("Drift", health.drift),
        ("Churn", health.churn),
        ("Complexity", health.complexity),
    ]

    for name, score in dimensions:
        color = _score_color(score)
        status = _status_label(score)
        table.add_row(
            name,
            f"[bold {color}]{score:.0%}[/bold {color}]",
            _bar(score),
            f"[{color}]{status}[/{color}]",
        )

    # Territory / succession metadata
    meta = []
    if health.territory:
        meta.append(f"Territory: [yellow]{health.territory}[/yellow]")
    if health.succession:
        meta.append(f"Succession: [green]{health.succession}[/green]")
    meta_text = "  |  ".join(meta) if meta else ""

    panel = Panel(
        table,
        subtitle=meta_text,
        border_style=overall_color,
    )

    # Return the renderable (caller should use Console().print)
    return panel


def _bar(score: float, width: int = 20) -> str:
    """Build an ASCII progress bar for a 0.0–1.0 score."""
    filled = int(score * width)
    empty = width - filled
    color = _score_color(score)
    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


def _score_color(score: float) -> str:
    """Map a score to a Rich color."""
    if score >= 0.8:
        return "green"
    elif score >= 0.6:
        return "yellow"
    elif score >= 0.4:
        return "orange3"
    else:
        return "red"


def _status_label(score: float) -> str:
    """Map a score to a status label."""
    if score >= 0.8:
        return "Thriving"
    elif score >= 0.6:
        return "Healthy"
    elif score >= 0.4:
        return "Stressed"
    elif score >= 0.2:
        return "Wilting"
    else:
        return "Critical"
