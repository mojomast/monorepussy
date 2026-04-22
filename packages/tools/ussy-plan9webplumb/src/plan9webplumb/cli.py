"""Command-line interface for Plan9-WebPlumb."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from plan9webplumb import __version__
from plan9webplumb.config import Config
from plan9webplumb.handlers import HandlerRegistry
from plan9webplumb.models import Handler, HandlerAction, HandlerRule, MessageType, PlumbMessage
from plan9webplumb.plumber import Plumber, run_server


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="plan9webplumb",
        description="Plan9-WebPlumb: A modernized Plan 9 Plumb server for the browser",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Path to configuration directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the plumber WebSocket server")
    serve_parser.add_argument("--host", default=None, help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=None, help="Port to listen on")

    # handlers
    handlers_parser = subparsers.add_parser("handlers", help="Manage handlers")
    handlers_sub = handlers_parser.add_subparsers(dest="handler_command", help="Handler commands")

    # handlers list
    handlers_sub.add_parser("list", help="List registered handlers")

    # handlers add
    add_parser = handlers_sub.add_parser("add", help="Add a new handler")
    add_parser.add_argument("--name", required=True, help="Handler name")
    add_parser.add_argument("--command", required=True, help="Command to execute")
    add_parser.add_argument("--action", choices=["exec", "pipe", "notify"], default="exec")
    add_parser.add_argument("--description", default="")
    add_parser.add_argument("--working-dir", default="")
    add_parser.add_argument("--timeout", type=float, default=30.0)
    add_parser.add_argument("--pattern", default="", help="URL/content regex pattern for auto-created rule")
    add_parser.add_argument("--msg-type", default="", help="Message type filter for rule")

    # handlers test
    test_parser = handlers_sub.add_parser("test", help="Test handler matching against sample data")
    test_parser.add_argument("--data", default="", help="Sample data text")
    test_parser.add_argument("--url", default="", help="Sample URL")
    test_parser.add_argument("--type", dest="msg_type", default="text", help="Message type")
    test_parser.add_argument("--src", default="browser", help="Message source")

    # handlers remove
    remove_parser = handlers_sub.add_parser("remove", help="Remove a handler")
    remove_parser.add_argument("name", help="Handler name to remove")

    # status
    subparsers.add_parser("status", help="Show plumber server status")

    return parser


def cmd_serve(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'serve' command."""
    if args.host:
        config._server_config["host"] = args.host
    if args.port:
        config._server_config["port"] = args.port
    run_server(config)


def cmd_handlers_list(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'handlers list' command."""
    registry = HandlerRegistry(config)
    registry.load()

    handlers = registry.handlers
    rules = registry.rules

    if not handlers and not rules:
        print("No handlers or rules configured.")
        return

    if handlers:
        print("Handlers:")
        for name, handler in sorted(handlers.items()):
            status = "enabled" if handler.enabled else "disabled"
            print(f"  {name} ({status}): {handler.command}")
            if handler.description:
                print(f"    {handler.description}")

    if rules:
        print("\nRules:")
        for rule in rules:
            status = "enabled" if rule.enabled else "disabled"
            print(f"  {rule.name} ({status}): pattern={rule.pattern!r} -> handler={rule.handler}")
            if rule.msg_type:
                print(f"    type filter: {rule.msg_type}")


def cmd_handlers_add(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'handlers add' command."""
    registry = HandlerRegistry(config)
    registry.load()

    handler = Handler(
        name=args.name,
        command=args.command,
        action=HandlerAction(args.action),
        description=args.description,
        working_dir=args.working_dir,
        timeout=args.timeout,
    )
    registry.add_handler(handler)
    print(f"Handler '{handler.name}' added.")

    # Optionally create a rule too
    if args.pattern:
        rule = HandlerRule(
            name=f"{handler.name}_rule",
            pattern=args.pattern,
            handler=handler.name,
            msg_type=args.msg_type,
        )
        registry.add_rule(rule)
        print(f"Rule '{rule.name}' added (pattern: {rule.pattern!r} -> {rule.handler}).")
    else:
        # Always create a default rule that matches the handler name
        rule = HandlerRule(
            name=f"{handler.name}_rule",
            pattern=args.pattern or "",
            handler=handler.name,
            msg_type=args.msg_type,
        )
        registry.add_rule(rule)
        if not args.pattern:
            print(f"Note: No --pattern specified. Rule '{rule.name}' will match all messages.")


def cmd_handlers_test(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'handlers test' command."""
    registry = HandlerRegistry(config)
    registry.load()

    message = PlumbMessage(
        src=args.src,
        msg_type=MessageType(args.msg_type),
        data=args.data,
        url=args.url,
    )

    matches = registry.test_match(message)

    if not matches:
        print("No matching handlers for the given input.")
        return

    print(f"Message: type={message.msg_type.value}, data={message.data!r}, url={message.url!r}")
    print(f"\n{len(matches)} matching rule(s):")
    for rule, handler in matches:
        handler_info = handler.command if handler else "(not found)"
        print(f"  Rule: {rule.name} (pattern: {rule.pattern!r})")
        print(f"  Handler: {rule.handler} -> {handler_info}")
        print()


def cmd_handlers_remove(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'handlers remove' command."""
    registry = HandlerRegistry(config)
    registry.load()

    removed = registry.remove_handler(args.name)
    if removed:
        print(f"Handler '{args.name}' removed.")
    else:
        print(f"Handler '{args.name}' not found.")


def cmd_status(args: argparse.Namespace, config: Config) -> None:
    """Handle the 'status' command."""
    registry = HandlerRegistry(config)
    registry.load()

    plumber = Plumber(config)
    status = plumber.get_status()

    print("Plan9-WebPlumb Status")
    print("=" * 40)
    print(f"  Version:     {__version__}")
    print(f"  Running:     {status['running']}")
    print(f"  Host:        {status['host']}")
    print(f"  Port:        {status['port']}")
    print(f"  Handlers:    {status['handlers_loaded']}")
    print(f"  Rules:       {status['rules_loaded']}")
    print(f"  Config dir:  {config.config_dir}")

    if status["stats"]["start_time"]:
        print(f"  Started:     {status['stats']['start_time']}")
        print(f"  Uptime:      {status['stats']['uptime_seconds']:.0f}s")
        print(f"  Messages:    {status['stats']['messages_received']} received")
        print(f"  Dispatched:  {status['stats']['messages_dispatched']}")
        print(f"  Fired:       {status['stats']['handlers_fired']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    config = Config(config_dir=args.config_dir) if args.config_dir else Config()

    if args.command == "serve":
        cmd_serve(args, config)
    elif args.command == "handlers":
        if not args.handler_command:
            parser.parse_args(["handlers", "--help"])
            return 0

        if args.handler_command == "list":
            cmd_handlers_list(args, config)
        elif args.handler_command == "add":
            cmd_handlers_add(args, config)
        elif args.handler_command == "test":
            cmd_handlers_test(args, config)
        elif args.handler_command == "remove":
            cmd_handlers_remove(args, config)
    elif args.command == "status":
        cmd_status(args, config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
