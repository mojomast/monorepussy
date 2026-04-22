"""Command-line interface for Mushin.

Usage::

    mushin init                         # Initialize .mushin in the project
    mushin save [-n NAME] [-d DESC]     # Save current workspace
    mushin resume [WORKSPACE_ID]        # Resume a workspace
    mushin list                         # List all workspaces
    mushin delete WORKSPACE_ID          # Delete a workspace
    mushin record EXPR [-o OUTPUT]      # Record a journal entry
    mushin journal [WORKSPACE_ID]       # Show the evaluation journal
    mushin replay [WORKSPACE_ID]        # Replay the journal
    mushin branch NAME [-p PARENT]      # Create a workspace branch
    mushin branches                     # List branches
    mushin bookmark NAME [-f FILE] [-l LINE]  # Create a spatial bookmark
    mushin bookmarks                    # List bookmarks
    mushin diff LEFT RIGHT              # Compare two workspaces
    mushin info                         # Show active workspace info
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ussy_mushin import __version__


def _project_dir(args: argparse.Namespace) -> Path:
    """Determine the project directory from args (defaults to cwd)."""
    d = getattr(args, "project_dir", None) or "."
    return Path(d).resolve()


# ---- Subcommand handlers ---------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    from ussy_mushin.storage import mushin_root

    project_dir = _project_dir(args)
    root = mushin_root(project_dir)
    print(f"Initialized mushin workspace at {root}")
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id

    project_dir = _project_dir(args)
    active_id = get_active_workspace_id(project_dir)

    if active_id:
        ws = Workspace.load(project_dir, active_id)
        if args.name:
            ws.meta.name = args.name
        if args.description:
            ws.meta.description = args.description
    else:
        ws = Workspace.create(
            project_dir,
            name=args.name or "",
            description=args.description or "",
        )
        ws.set_active()

    ws.save()
    print(f"Saved workspace {ws.id} ({ws.meta.name})")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id

    project_dir = _project_dir(args)
    workspace_id = args.workspace_id or get_active_workspace_id(project_dir)
    if not workspace_id:
        print("No workspace specified and no active workspace found.", file=sys.stderr)
        return 1

    ws = Workspace.load(project_dir, workspace_id)
    ws.set_active()
    print(f"Resumed workspace {ws.id} ({ws.meta.name})")
    print(f"  Created:  {ws.meta.created_at}")
    print(f"  Last saved: {ws.meta.saved_at}")
    print(f"  Journal entries: {len(ws.journal)}")
    print(f"  Objects: {len(ws.list_objects())}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import list_workspaces, get_active_workspace_id

    project_dir = _project_dir(args)
    workspaces = list_workspaces(project_dir)
    active_id = get_active_workspace_id(project_dir)

    if not workspaces:
        print("No workspaces found.")
        return 0

    for meta in workspaces:
        marker = " *" if meta.id == active_id else "  "
        name = meta.name or meta.id[:8]
        branch = f" [{meta.branch_name}]" if meta.branch_name else ""
        print(f"{marker} {meta.id[:16]}  {name}{branch}  {meta.saved_at}")

    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import delete_workspace

    project_dir = _project_dir(args)
    delete_workspace(project_dir, args.workspace_id)
    print(f"Deleted workspace {args.workspace_id}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id

    project_dir = _project_dir(args)
    workspace_id = get_active_workspace_id(project_dir)
    if not workspace_id:
        # Auto-create a workspace
        ws = Workspace.create(project_dir, name="auto")
        ws.set_active()
        ws.save()
        workspace_id = ws.id

    ws = Workspace.load(project_dir, workspace_id)
    entry = ws.journal.record(
        expression=args.expression,
        output=args.output or "",
        result_type=args.type or "success",
    )
    ws.save()
    print(f"Recorded entry [{entry.result_type}] >>> {entry.expression}")
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id

    project_dir = _project_dir(args)
    workspace_id = args.workspace_id or get_active_workspace_id(project_dir)
    if not workspace_id:
        print("No workspace specified and no active workspace found.", file=sys.stderr)
        return 1

    ws = Workspace.load(project_dir, workspace_id)
    print(ws.journal.export_text())
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id

    project_dir = _project_dir(args)
    workspace_id = args.workspace_id or get_active_workspace_id(project_dir)
    if not workspace_id:
        print("No workspace specified and no active workspace found.", file=sys.stderr)
        return 1

    ws = Workspace.load(project_dir, workspace_id)
    results = ws.journal.replay()
    for expr, output in results:
        print(f">>> {expr}")
        if output:
            print(output)
        print()
    return 0


def cmd_branch(args: argparse.Namespace) -> int:
    from ussy_mushin.branching import BranchManager
    from ussy_mushin.workspace import get_active_workspace_id

    project_dir = _project_dir(args)
    parent_id = args.parent or get_active_workspace_id(project_dir)
    if not parent_id:
        print("No parent workspace specified and no active workspace found.", file=sys.stderr)
        return 1

    mgr = BranchManager(project_dir)
    child = mgr.create_branch(
        name=args.name,
        parent_workspace_id=parent_id,
        description=args.description or "",
    )
    child.set_active()
    print(f"Created branch '{args.name}' → workspace {child.id}")
    return 0


def cmd_branches(args: argparse.Namespace) -> int:
    from ussy_mushin.branching import BranchManager

    project_dir = _project_dir(args)
    mgr = BranchManager(project_dir)
    branches = mgr.list_branches()

    if not branches:
        print("No branches found.")
        return 0

    for b in branches:
        print(f"  {b.name}  → {b.workspace_id[:16]}  (from {b.parent_id[:16]})  {b.created_at}")
    return 0


def cmd_bookmark(args: argparse.Namespace) -> int:
    from ussy_mushin.bookmarks import BookmarkManager
    from ussy_mushin.workspace import get_active_workspace_id

    project_dir = _project_dir(args)
    workspace_id = get_active_workspace_id(project_dir) or ""

    mgr = BookmarkManager(project_dir)
    bm = mgr.add(
        name=args.name,
        file_path=args.file or "",
        line=args.line or 0,
        column=args.column or 0,
        annotation=args.annotation or "",
        workspace_id=workspace_id,
        tags=args.tags.split(",") if args.tags else [],
    )
    print(f"Bookmark '{bm.name}' set at {bm.file_path}:{bm.line}")
    return 0


def cmd_bookmarks(args: argparse.Namespace) -> int:
    from ussy_mushin.bookmarks import BookmarkManager

    project_dir = _project_dir(args)
    mgr = BookmarkManager(project_dir)
    bookmarks = mgr.list_bookmarks()

    if not bookmarks:
        print("No bookmarks found.")
        return 0

    for b in bookmarks:
        loc = f"{b.file_path}:{b.line}" if b.file_path else "no location"
        tags = f" [{', '.join(b.tags)}]" if b.tags else ""
        ann = f" — {b.annotation}" if b.annotation else ""
        print(f"  {b.name}  {loc}{tags}{ann}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace
    from ussy_mushin.diff import diff_workspaces

    project_dir = _project_dir(args)
    left = Workspace.load(project_dir, args.left)
    right = Workspace.load(project_dir, args.right)

    result = diff_workspaces(left, right)
    if not result.has_changes:
        print("No differences found.")
    else:
        print(result.summary())
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from ussy_mushin.workspace import Workspace, get_active_workspace_id, list_workspaces
    from ussy_mushin.branching import BranchManager
    from ussy_mushin.bookmarks import BookmarkManager

    project_dir = _project_dir(args)
    active_id = get_active_workspace_id(project_dir)
    workspaces = list_workspaces(project_dir)
    mgr = BranchManager(project_dir)
    bm_mgr = BookmarkManager(project_dir)

    print("Mushin Workspace Info")
    print(f"  Project: {project_dir}")
    print(f"  Active workspace: {active_id or '(none)'}")
    print(f"  Total workspaces: {len(workspaces)}")
    print(f"  Branches: {len(mgr.list_branches())}")
    print(f"  Bookmarks: {len(bm_mgr.list_bookmarks())}")
    return 0


# ---- Argument parser -------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mushin",
        description="Mushin — Persistent live workspace for code exploration",
    )
    parser.add_argument("--version", action="version", version=f"mushin {__version__}")
    parser.add_argument("-C", "--project-dir", default=".", help="Project directory (default: cwd)")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="Initialize mushin in the project")
    p_init.set_defaults(func=cmd_init)

    # save
    p_save = sub.add_parser("save", help="Save current workspace")
    p_save.add_argument("-n", "--name", default="", help="Workspace name")
    p_save.add_argument("-d", "--description", default="", help="Description")
    p_save.set_defaults(func=cmd_save)

    # resume
    p_resume = sub.add_parser("resume", help="Resume a workspace")
    p_resume.add_argument("workspace_id", nargs="?", default="", help="Workspace ID to resume")
    p_resume.set_defaults(func=cmd_resume)

    # list
    p_list = sub.add_parser("list", help="List all workspaces")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a workspace")
    p_delete.add_argument("workspace_id", help="Workspace ID to delete")
    p_delete.set_defaults(func=cmd_delete)

    # record
    p_record = sub.add_parser("record", help="Record a journal entry")
    p_record.add_argument("expression", help="Expression to record")
    p_record.add_argument("-o", "--output", default="", help="Output of the expression")
    p_record.add_argument("-t", "--type", default="success", help="Result type: success|error|info")
    p_record.set_defaults(func=cmd_record)

    # journal
    p_journal = sub.add_parser("journal", help="Show the evaluation journal")
    p_journal.add_argument("workspace_id", nargs="?", default="", help="Workspace ID")
    p_journal.set_defaults(func=cmd_journal)

    # replay
    p_replay = sub.add_parser("replay", help="Replay the journal")
    p_replay.add_argument("workspace_id", nargs="?", default="", help="Workspace ID")
    p_replay.set_defaults(func=cmd_replay)

    # branch
    p_branch = sub.add_parser("branch", help="Create a workspace branch")
    p_branch.add_argument("name", help="Branch name")
    p_branch.add_argument("-p", "--parent", default="", help="Parent workspace ID")
    p_branch.add_argument("-d", "--description", default="", help="Branch description")
    p_branch.set_defaults(func=cmd_branch)

    # branches
    p_branches = sub.add_parser("branches", help="List branches")
    p_branches.set_defaults(func=cmd_branches)

    # bookmark
    p_bookmark = sub.add_parser("bookmark", help="Create a spatial bookmark")
    p_bookmark.add_argument("name", help="Bookmark name")
    p_bookmark.add_argument("-f", "--file", default="", help="File path")
    p_bookmark.add_argument("-l", "--line", type=int, default=0, help="Line number")
    p_bookmark.add_argument("-c", "--column", type=int, default=0, help="Column number")
    p_bookmark.add_argument("-a", "--annotation", default="", help="Annotation text")
    p_bookmark.add_argument("-t", "--tags", default="", help="Comma-separated tags")
    p_bookmark.set_defaults(func=cmd_bookmark)

    # bookmarks
    p_bookmarks = sub.add_parser("bookmarks", help="List bookmarks")
    p_bookmarks.set_defaults(func=cmd_bookmarks)

    # diff
    p_diff = sub.add_parser("diff", help="Compare two workspaces")
    p_diff.add_argument("left", help="Left workspace ID")
    p_diff.add_argument("right", help="Right workspace ID")
    p_diff.set_defaults(func=cmd_diff)

    # info
    p_info = sub.add_parser("info", help="Show workspace info")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
