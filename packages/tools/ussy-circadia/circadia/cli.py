"""CLI interface for Circadia."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

from circadia import __version__
from circadia.zones import CognitiveZone, ZoneProbability
from circadia.estimator import CircadianEstimator
from circadia.config import CircadiaConfig
from circadia.session import SessionTracker
from circadia.hooks import GitHooksManager
from circadia.indicator import TerminalIndicator
from circadia.linter import LinterAdapter


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the Circadia CLI."""
    parser = argparse.ArgumentParser(
        prog="circadia",
        description="Circadia — Circadian rhythm-aware development environment",
    )
    parser.add_argument(
        "--version", action="version", version=f"circadia {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    status_parser = subparsers.add_parser(
        "status", help="Show current cognitive zone"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )
    status_parser.add_argument(
        "--prompt", action="store_true", help="Output short prompt string"
    )
    status_parser.add_argument(
        "--full", action="store_true", help="Show full zone details"
    )

    # hooks
    hooks_parser = subparsers.add_parser("hooks", help="Manage git hooks")
    hooks_sub = hooks_parser.add_subparsers(
        dest="hooks_command", help="Hook commands"
    )
    hooks_sub.add_parser("install", help="Install Circadia git hooks")
    hooks_sub.add_parser("remove", help="Remove Circadia git hooks")
    hooks_check = hooks_sub.add_parser(
        "check", help="Check if a git operation is allowed"
    )
    hooks_check.add_argument(
        "operation",
        choices=["force_push", "hard_reset", "delete_branch", "deploy_production"],
        help="Operation to check",
    )
    hooks_check.add_argument(
        "--override", action="store_true",
        help="Include override flag in check",
    )

    # session
    session_parser = subparsers.add_parser("session", help="Manage coding sessions")
    session_sub = session_parser.add_subparsers(
        dest="session_command", help="Session commands"
    )
    session_sub.add_parser("start", help="Start a new coding session")
    session_sub.add_parser("end", help="End the current coding session")
    session_sub.add_parser("status", help="Show current session status")

    # config
    config_parser = subparsers.add_parser("config", help="View or edit configuration")
    config_parser.add_argument(
        "--set", nargs=2, metavar=("KEY", "VALUE"), help="Set a config value"
    )
    config_parser.add_argument(
        "--show", action="store_true", help="Show current configuration"
    )
    config_parser.add_argument(
        "--init", action="store_true", help="Initialize config with defaults"
    )

    # linter
    linter_parser = subparsers.add_parser("linter", help="Show linter configuration for current zone")
    linter_parser.add_argument(
        "--zone",
        choices=["green", "yellow", "red", "creative"],
        help="Show linter config for a specific zone",
    )

    return parser


def _cmd_status(args: argparse.Namespace, config: CircadiaConfig) -> int:
    """Handle the 'status' command."""
    estimator = CircadianEstimator(utc_offset_hours=config.utc_offset_hours)
    tracker = SessionTracker()
    indicator = TerminalIndicator(config=config, estimator=estimator, session_tracker=tracker)

    session_hours = tracker.get_current_duration_hours()
    now = datetime.now(timezone.utc)
    prob = estimator.estimate(now, session_hours)
    zone = prob.dominant_zone

    if getattr(args, "prompt", False):
        print(indicator.short_indicator(now))
        return 0

    if getattr(args, "json", False):
        data = {
            "zone": zone.value,
            "icon": zone.icon,
            "confidence": prob.confidence,
            "probabilities": {
                "green": prob.green,
                "yellow": prob.yellow,
                "red": prob.red,
                "creative": prob.creative,
            },
            "session_hours": session_hours,
            "utc_offset": config.utc_offset_hours,
            "local_hour": estimator._local_hour(now),
        }
        print(json.dumps(data, indent=2))
        return 0

    if getattr(args, "full", False):
        print(indicator.full_indicator(now))
        return 0

    # Default: colored indicator
    print(indicator.colored_indicator(now))
    print(f"  {zone.description}")
    if session_hours > 0:
        hours = int(session_hours)
        mins = int((session_hours - hours) * 60)
        print(f"  Session: {hours}h {mins}m")
    return 0


def _cmd_hooks(args: argparse.Namespace, config: CircadiaConfig) -> int:
    """Handle the 'hooks' command."""
    hooks_command = getattr(args, "hooks_command", None)

    if hooks_command == "install":
        manager = GitHooksManager(config=config)
        try:
            installed = manager.install_all()
            for name in installed:
                print(f"✅ Installed hook: {name}")
            return 0
        except RuntimeError as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            return 1

    elif hooks_command == "remove":
        manager = GitHooksManager(config=config)
        removed = manager.remove_all()
        if removed:
            for name in removed:
                print(f"🗑️  Removed hook: {name}")
        else:
            print("No Circadia hooks found to remove.")
        return 0

    elif hooks_command == "check":
        operation = getattr(args, "operation", None)
        override = getattr(args, "override", False)
        if not operation:
            print("Error: operation required for 'hooks check'", file=sys.stderr)
            return 1
        manager = GitHooksManager(config=config)
        result = manager.check_operation(operation, override=override)
        if result.allowed:
            print(f"✅ {result.message}")
        else:
            print(f"🚫 {result.message}")
        return 0 if result.allowed else 1

    else:
        print("Usage: circadia hooks {install|remove|check}", file=sys.stderr)
        return 1


def _cmd_session(args: argparse.Namespace, config: CircadiaConfig) -> int:
    """Handle the 'session' command."""
    session_command = getattr(args, "session_command", None)
    tracker = SessionTracker()

    if session_command == "start":
        try:
            session = tracker.start_session()
            print(f"🟢 Session started at {session.start_time}")
            return 0
        except RuntimeError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 1

    elif session_command == "end":
        try:
            session = tracker.end_session()
            duration = session.duration_hours()
            hours = int(duration)
            mins = int((duration - hours) * 60)
            print(f"🔴 Session ended at {session.end_time} (duration: {hours}h {mins}m)")
            return 0
        except RuntimeError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 1

    elif session_command == "status":
        active = tracker.get_active_session()
        if active:
            duration = active.duration_hours()
            hours = int(duration)
            mins = int((duration - hours) * 60)
            print(f"🟢 Active session since {active.start_time}")
            print(f"   Duration: {hours}h {mins}m")
        else:
            print("⚪ No active session")
        return 0

    else:
        print("Usage: circadia session {start|end|status}", file=sys.stderr)
        return 1


def _cmd_config(args: argparse.Namespace, config: CircadiaConfig) -> int:
    """Handle the 'config' command."""
    if getattr(args, "init", False):
        config.save()
        print("✅ Configuration initialized with defaults.")
        return 0

    if getattr(args, "set", None):
        key, value = args.set
        # Support nested keys with dot notation
        if key == "utc_offset_hours":
            config.utc_offset_hours = float(value)
        elif key == "work_start_hour":
            config.work_start_hour = float(value)
        elif key == "work_end_hour":
            config.work_end_hour = float(value)
        elif key == "session_duration_limit_hours":
            config.session_duration_limit_hours = float(value)
        else:
            print(f"⚠️  Unknown config key: {key}", file=sys.stderr)
            return 1
        config.save()
        print(f"✅ Set {key} = {value}")
        return 0

    # Default: show config
    print(json.dumps(config.to_dict(), indent=2))
    return 0


def _cmd_linter(args: argparse.Namespace, config: CircadiaConfig) -> int:
    """Handle the 'linter' command."""
    adapter = LinterAdapter(config=config)

    zone_name = getattr(args, "zone", None)
    if zone_name:
        zone = CognitiveZone(zone_name)
    else:
        estimator = CircadianEstimator(utc_offset_hours=config.utc_offset_hours)
        tracker = SessionTracker()
        session_hours = tracker.get_current_duration_hours()
        zone = estimator.current_zone(
            dt=datetime.now(timezone.utc),
            session_hours=session_hours,
        )

    print(adapter.format_linter_config(zone))
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the Circadia CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 0

    # Load config
    config = CircadiaConfig.load()

    dispatch = {
        "status": _cmd_status,
        "hooks": _cmd_hooks,
        "session": _cmd_session,
        "config": _cmd_config,
        "linter": _cmd_linter,
    }

    handler = dispatch.get(command)
    if handler:
        return handler(args, config)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
