"""Snapshot CLI — command-line interface using argparse."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="snapshot",
        description="Snapshot — Freeze and thaw your entire development state",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # save
    save_parser = subparsers.add_parser("save", help="Save current development state as a named snapshot")
    save_parser.add_argument("name", help="Name for the snapshot")
    save_parser.add_argument("--note", "-n", default="", help="Mental context note — what you were about to do")
    save_parser.add_argument("--project-dir", "-d", default="", help="Project directory (default: current)")
    save_parser.add_argument("--include-secrets", action="store_true", help="Include secret env vars")

    # load
    load_parser = subparsers.add_parser("load", help="Load a previously saved snapshot")
    load_parser.add_argument("name", help="Name of the snapshot to load")
    load_parser.add_argument("--dry-run", action="store_true", help="Show what would be restored without making changes")

    # new
    new_parser = subparsers.add_parser("new", help="Create a clean environment snapshot")
    new_parser.add_argument("name", help="Name for the new snapshot")
    new_parser.add_argument("--project-dir", "-d", default="", help="Project directory (default: current)")

    # list
    list_parser = subparsers.add_parser("list", help="List all snapshots with metadata")
    list_parser.add_argument("--sort", choices=["age", "size", "name"], default="age", help="Sort order")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")

    # peek
    peek_parser = subparsers.add_parser("peek", help="Show what's in a snapshot without loading it")
    peek_parser.add_argument("name", help="Name of the snapshot to peek at")

    # prune
    prune_parser = subparsers.add_parser("prune", help="Delete old snapshots")
    prune_parser.add_argument("--older-than", default="", help="Delete snapshots older than duration (e.g. 7d, 2h)")
    prune_parser.add_argument("--keep-last", type=int, default=0, help="Keep at least N most recent snapshots")
    prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")

    # diff
    diff_parser = subparsers.add_parser("diff", help="Diff two snapshots")
    diff_parser.add_argument("name1", help="First snapshot name")
    diff_parser.add_argument("name2", help="Second snapshot name")

    # export
    export_parser = subparsers.add_parser("export", help="Export snapshot for sharing")
    export_parser.add_argument("name", help="Snapshot name to export")
    export_parser.add_argument("--output", "-o", default="", help="Output file path (default: <name>.tar.gz)")
    export_parser.add_argument("--include-secrets", action="store_true", help="Include secret env vars in export")

    # import
    import_parser = subparsers.add_parser("import", help="Import a snapshot from an archive")
    import_parser.add_argument("path", help="Path to the snapshot archive")
    import_parser.add_argument("--name", default="", help="New name for the imported snapshot")

    # tag
    tag_parser = subparsers.add_parser("tag", help="Tag a snapshot for long-term retention")
    tag_parser.add_argument("name", help="Snapshot name")
    tag_parser.add_argument("tag", help="Tag to add")

    # untag
    untag_parser = subparsers.add_parser("untag", help="Remove a tag from a snapshot")
    untag_parser.add_argument("name", help="Snapshot name")
    untag_parser.add_argument("tag", help="Tag to remove")

    return parser


def cmd_save(args: argparse.Namespace) -> int:
    """Handle the 'save' command."""
    from .core import save
    snapshot = save(
        name=args.name,
        note=getattr(args, "note", ""),
        project_dir=getattr(args, "project_dir", ""),
        include_secrets=getattr(args, "include_secrets", False),
    )
    print(f"✅ Saved snapshot: {snapshot.name}")
    print(f"   Terminals: {len(snapshot.terminals)}, "
          f"Files: {len(snapshot.editor.open_files)}, "
          f"Processes: {len(snapshot.processes)}")
    if snapshot.mental_context.note:
        print(f"   Note: \"{snapshot.mental_context.note}\"")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    """Handle the 'load' command."""
    from .core import load
    snapshot = load(args.name, dry_run=getattr(args, "dry_run", False))
    if snapshot is None:
        print(f"❌ Snapshot not found: {args.name}", file=sys.stderr)
        return 1
    print(f"\n✅ Loaded snapshot: {snapshot.name}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Handle the 'new' command."""
    from .core import new
    snapshot = new(
        name=args.name,
        project_dir=getattr(args, "project_dir", ""),
    )
    print(f"✅ Created clean snapshot: {snapshot.name}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Handle the 'list' command."""
    from .core import format_snapshot_list
    from .storage import list_snapshots
    snapshots = list_snapshots(sort=getattr(args, "sort", "age"))
    verbose = getattr(args, "verbose", False)
    output = format_snapshot_list(snapshots, verbose=verbose)
    print(output)
    return 0


def cmd_peek(args: argparse.Namespace) -> int:
    """Handle the 'peek' command."""
    from .core import peek
    result = peek(args.name)
    if result is None:
        print(f"❌ Snapshot not found: {args.name}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """Handle the 'prune' command."""
    from .prune import prune_snapshots
    deleted = prune_snapshots(
        older_than=getattr(args, "older_than", ""),
        keep_last=getattr(args, "keep_last", 0),
        dry_run=getattr(args, "dry_run", False),
    )
    if deleted:
        action = "Would delete" if getattr(args, "dry_run", False) else "Deleted"
        print(f"🗑️  {action} {len(deleted)} snapshot(s):")
        for name in deleted:
            print(f"  - {name}")
    else:
        print("No snapshots to prune.")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Handle the 'diff' command."""
    from .diff import diff_snapshots, format_diff
    result = diff_snapshots(args.name1, args.name2)
    if "error" in result:
        print(f"❌ {result['error']}", file=sys.stderr)
        return 1
    print(format_diff(result))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Handle the 'export' command."""
    from .export import export_snapshot
    try:
        output = export_snapshot(
            name=args.name,
            output_path=getattr(args, "output", ""),
            include_secrets=getattr(args, "include_secrets", False),
        )
        print(f"📦 Exported snapshot to: {output}")
        return 0
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


def cmd_import(args: argparse.Namespace) -> int:
    """Handle the 'import' command."""
    from .export import import_snapshot
    try:
        name = import_snapshot(
            archive_path=args.path,
            new_name=getattr(args, "name", ""),
        )
        print(f"📥 Imported snapshot: {name}")
        return 0
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


def cmd_tag(args: argparse.Namespace) -> int:
    """Handle the 'tag' command."""
    from .core import tag
    if tag(args.name, args.tag):
        print(f"🏷️  Tagged '{args.name}' with '{args.tag}'")
        return 0
    else:
        print(f"❌ Snapshot not found: {args.name}", file=sys.stderr)
        return 1


def cmd_untag(args: argparse.Namespace) -> int:
    """Handle the 'untag' command."""
    from .core import untag
    if untag(args.name, args.tag):
        print(f"🏷️  Removed tag '{args.tag}' from '{args.name}'")
        return 0
    else:
        print(f"❌ Snapshot not found: {args.name}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    dispatch = {
        "save": cmd_save,
        "load": cmd_load,
        "new": cmd_new,
        "list": cmd_list,
        "peek": cmd_peek,
        "prune": cmd_prune,
        "diff": cmd_diff,
        "export": cmd_export,
        "import": cmd_import,
        "tag": cmd_tag,
        "untag": cmd_untag,
    }

    handler = dispatch.get(command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
