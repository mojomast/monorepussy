"""CLI interface for Kintsugi — Visible Repair History."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional

from . import __version__
from .joint import Joint, JointStore
from .scanner import scan_file, scan_directory, insert_annotation
from .scar_map import build_scar_map, format_scar_map, find_hotspots
from .stress import stress_test_joint, stress_test_all
from .archaeology import build_archaeology_report, format_archaeology_report


def cmd_mark(args):
    """Mark a bug fix as a golden joint."""
    # Parse file:line from location
    location = args.location
    line_number = 1
    file_path = location

    if ":" in location:
        parts = location.rsplit(":", 1)
        try:
            line_number = int(parts[1])
            file_path = parts[0]
        except ValueError:
            pass

    now = datetime.now(timezone.utc)
    severity = args.severity or "warning"

    joint = Joint(
        file=file_path,
        line=line_number,
        timestamp=now.isoformat(),
        bug_ref=args.bug or "UNKNOWN",
        severity=severity,
        break_description=args.break_desc or "",
        repair_description=args.repair or "",
        removal_impact=args.removal_impact or "",
        test_ref=args.test or "",
        status="solid_gold",
    )

    # Save to store
    store = JointStore()
    store.save(joint)

    # Insert inline annotation if the file exists
    try:
        with open(file_path, "r"):
            pass
        insert_annotation(
            file_path=file_path,
            line_number=line_number,
            bug_ref=joint.bug_ref,
            severity=joint.severity,
            break_description=joint.break_description,
            repair_description=joint.repair_description,
            removal_impact=joint.removal_impact,
            test_ref=joint.test_ref,
            timestamp=now.strftime("%Y-%m-%d"),
        )
        print(f"✅ Golden joint marked and annotation inserted: {joint.id}")
    except FileNotFoundError:
        print(f"✅ Golden joint marked (file not found, annotation skipped): {joint.id}")

    print(f"   File: {joint.file}:{joint.line}")
    print(f"   Bug:  {joint.bug_ref} ({joint.severity})")
    print(f"   Break: {joint.break_description}")


def cmd_map(args):
    """Generate a scar map of the codebase."""
    target = args.path or "."
    root = args.root or "."

    # Load joints from store
    store = JointStore(root)
    joints = store.load_all()

    if not joints:
        # Also try scanning the target directory
        results = scan_directory(target)
        joints = []
        for r in results:
            joints.extend(r.joints)

    if not joints:
        print("No golden joints found. Use 'kintsugi mark' to create your first joint.")
        return

    file_map = build_scar_map(root=root, joints=joints)
    output = format_scar_map(file_map, root=root)
    print(output)

    # Show hotspots
    hotspots = find_hotspots(file_map, threshold=args.threshold or 3)
    if hotspots:
        print(f"\n🔥 Hotspots ({len(hotspots)} files with ≥{args.threshold or 3} joints):")
        for path, count in hotspots:
            print(f"   {path}: {count} joints")


def cmd_stress(args):
    """Stress-test all golden joints."""
    root = args.root or "."
    junit_output = getattr(args, "junit_output", None)

    print("🏋️ Stress testing golden joints...")
    print("   (Removing repairs one at a time and running referenced tests)")
    print()

    report = stress_test_all(root=root, junit_output=junit_output)

    print(f"Results: {report.total} joints tested")
    print(f"  ⛩️ Solid gold (still needed): {report.solid_count}")
    print(f"  🕳️ Hollow (redundant):        {report.hollow_count}")
    print(f"  ❌ Error:                      {report.error_count}")
    print(f"  ⏭️ Untested:                   {report.untested_count}")

    if junit_output:
        print(f"\n📄 JUnit output written to: {junit_output}")

    # Show details for hollow joints
    hollow = [r for r in report.results if r.outcome == "hollow"]
    if hollow:
        print(f"\n🕳️ Hollow joints (repairs that may be redundant):")
        for r in hollow:
            print(f"   {r.joint_id} ({r.file}:{r.line})")
            print(f"     {r.message}")

    # Show details for errors
    errors = [r for r in report.results if r.outcome == "error"]
    if errors:
        print(f"\n❌ Errors:")
        for r in errors:
            print(f"   {r.joint_id}: {r.message}")


def cmd_archaeology(args):
    """Reconstruct the fracture history of a file."""
    file_path = args.file
    root = getattr(args, "root", ".") or "."

    report = build_archaeology_report(file_path, root=root)
    output = format_archaeology_report(report)
    print(output)


def cmd_hollow(args):
    """Find hollow joints (repairs that may be redundant)."""
    root = getattr(args, "root", ".") or "."
    store = JointStore(root)
    hollow_joints = store.find_hollow()

    if not hollow_joints:
        print("No hollow joints found. All repairs are solid gold! ⛩️")
        return

    print(f"🕳️ Hollow joints ({len(hollow_joints)} found):")
    print()
    for j in hollow_joints:
        print(f"  {j.id}")
        print(f"    File:   {j.file}:{j.line}")
        print(f"    Bug:    {j.bug_ref}")
        print(f"    Break:  {j.break_description}")
        print(f"    Repair: {j.repair_description}")
        print(f"    Impact: {j.removal_impact}")
        print()


def cmd_list(args):
    """List all golden joints."""
    root = getattr(args, "root", ".") or "."
    store = JointStore(root)
    joints = store.load_all()

    if not joints:
        print("No golden joints found.")
        return

    print(f"⛩️ Golden joints ({len(joints)} total):")
    print()
    for j in joints:
        severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(j.severity, "?")
        status_icon = {"solid_gold": "⛩️", "hollow": "🕳️", "untested": "❓"}.get(j.status, "?")
        print(f"  {severity_icon} {status_icon} {j.id}")
        print(f"      {j.file}:{j.line} | {j.bug_ref}")
        print(f"      {j.break_description[:60]}")
        print()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="kintsugi",
        description="Kintsugi — Visible Repair History That Makes Code Stronger at the Scars",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # mark
    mark_parser = subparsers.add_parser("mark", help="Mark a bug fix as a golden joint")
    mark_parser.add_argument("--bug", required=True, help="Bug reference (e.g., PROJ-892)")
    mark_parser.add_argument("--severity", choices=["critical", "warning", "info"], default="warning", help="Severity level")
    mark_parser.add_argument("--break-desc", required=True, help="What broke")
    mark_parser.add_argument("--repair", required=True, help="How it was repaired")
    mark_parser.add_argument("--removal-impact", default="", help="What happens if the repair is removed")
    mark_parser.add_argument("--test", default="", help="Reference to a stress test")
    mark_parser.add_argument("location", help="File:line location (e.g., src/auth/login.py:42)")

    # map
    map_parser = subparsers.add_parser("map", help="Generate a scar map of the codebase")
    map_parser.add_argument("path", nargs="?", default=".", help="Directory to scan")
    map_parser.add_argument("--root", default=".", help="Repository root path")
    map_parser.add_argument("--threshold", type=int, default=3, help="Hotspot threshold")

    # stress
    stress_parser = subparsers.add_parser("stress", help="Stress-test all golden joints")
    stress_parser.add_argument("--root", default=".", help="Repository root path")
    stress_parser.add_argument("--junit-output", default=None, help="Path for JUnit XML output")

    # archaeology
    arch_parser = subparsers.add_parser("archaeology", help="Reconstruct fracture history of a file")
    arch_parser.add_argument("file", help="File to analyze")
    arch_parser.add_argument("--root", default=".", help="Repository root path")

    # hollow
    hollow_parser = subparsers.add_parser("hollow", help="Find hollow joints (redundant repairs)")
    hollow_parser.add_argument("--root", default=".", help="Repository root path")

    # list
    list_parser = subparsers.add_parser("list", help="List all golden joints")
    list_parser.add_argument("--root", default=".", help="Repository root path")

    return parser


def main(argv: Optional[List[str]] = None):
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return

    commands = {
        "mark": cmd_mark,
        "map": cmd_map,
        "stress": cmd_stress,
        "archaeology": cmd_archaeology,
        "hollow": cmd_hollow,
        "list": cmd_list,
    }

    handler = commands.get(command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
