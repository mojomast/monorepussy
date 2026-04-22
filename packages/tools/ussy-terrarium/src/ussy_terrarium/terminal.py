"""Rich Live terminal watch mode for Terrarium."""

import time
from typing import Optional

from rich.console import Console
from rich.live import Live

from .engine import TerrariumEngine
from .viz import render_dashboard


def live_watch(engine: TerrariumEngine, interval: int = 5) -> None:
    """Run a live-updating dashboard in the terminal.

    Args:
        engine: A TerrariumEngine with adapters configured.
        interval: Seconds between refreshes.
    """
    console = Console()
    console.clear()

    with Live(
        console=console,
        refresh_per_second=1,
        screen=True,
    ) as live:
        while True:
            try:
                engine.collect()
                health = engine.score()
                panel = render_dashboard(health)
                live.update(panel)
                time.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n[dim]👋  Exiting watch mode.[/dim]")
                break
            except Exception as exc:
                console.print(f"[red]Error: {exc}[/red]")
                time.sleep(interval)
