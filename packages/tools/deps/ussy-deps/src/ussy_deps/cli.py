"""Unified CLI dispatcher for dependency analysis tools."""
import argparse
import sys
import warnings

def main():
    parser = argparse.ArgumentParser(
        prog="ussy-deps",
        description="Unified dependency analysis toolkit"
    )
    parser.add_argument("--version", action="version", version="ussy-deps 2025.1.0")
    
    subparsers = parser.add_subparsers(dest="tool", help="Available tools")
    
    # Gridiron
    p = subparsers.add_parser("gridiron", help="Power-grid dependency reliability")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for ussy-gridiron")
    
    # Chromato
    p = subparsers.add_parser("chromato", help="Chromatography risk analysis")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for ussy-chromato")
    
    # Cambium
    p = subparsers.add_parser("cambium", help="Grafting compatibility analysis")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for ussy-cambium")
    
    # Stratax
    p = subparsers.add_parser("stratax", help="Behavioral dependency probing")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for ussy-stratax")
    
    args = parser.parse_args()
    
    if not args.tool:
        parser.print_help()
        sys.exit(0)
    
    # Dispatch to the appropriate tool
    if args.tool == "gridiron":
        from ussy_gridiron.cli import main as gridiron_main
        sys.argv = ["ussy-gridiron"] + (args.args or [])
        gridiron_main()
    elif args.tool == "chromato":
        from ussy_chromato.cli import main as chromato_main
        sys.argv = ["ussy-chromato"] + (args.args or [])
        chromato_main()
    elif args.tool == "cambium":
        from ussy_cambium.cli import main as cambium_main
        sys.argv = ["ussy-cambium"] + (args.args or [])
        cambium_main()
    elif args.tool == "stratax":
        from ussy_stratax.cli import main as stratax_main
        sys.argv = ["ussy-stratax"] + (args.args or [])
        stratax_main()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
