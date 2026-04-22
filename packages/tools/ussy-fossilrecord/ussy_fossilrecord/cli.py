"""CLI interface for FossilRecord — the `fossil` command."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ussy_fossilrecord import __version__
from ussy_fossilrecord.corpus.loader import CorpusLoader, StressCategory, load_corpus
from ussy_fossilrecord.harness.runner import HarnessRunner, TestSuiteResult
from ussy_fossilrecord.harness.plugins import (
    ParserPlugin,
    LinterPlugin,
    FormatterPlugin,
    AIPlugin,
)
from ussy_fossilrecord.scoring.fossil_score import compute_fossil_score, FossilScore
from ussy_fossilrecord.generator.living_fossil import LivingFossilGenerator, GenerationConfig
from ussy_fossilrecord.compare.comparator import ToolComparator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fossil",
        description="FossilRecord — Esolang stress testing for developer tools",
    )
    parser.add_argument(
        "--version", action="version", version=f"fossil {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- test ---
    test_parser = subparsers.add_parser("test", help="Run full stress test suite")
    test_parser.add_argument(
        "--tool", "-t", default="unknown",
        help="Name of the tool being tested",
    )
    test_parser.add_argument(
        "--version", "-v", default="", dest="tool_version",
        help="Version of the tool",
    )
    test_parser.add_argument(
        "--language", "-l", action="append",
        help="Filter by esolang language (can repeat)",
    )
    test_parser.add_argument(
        "--category", "-c", action="append",
        choices=[c.value for c in StressCategory],
        help="Filter by stress category (can repeat)",
    )
    test_parser.add_argument(
        "--min-difficulty", type=int, default=1,
        help="Minimum difficulty level (1-5)",
    )
    test_parser.add_argument(
        "--max-difficulty", type=int, default=5,
        help="Maximum difficulty level (1-5)",
    )
    test_parser.add_argument(
        "--timeout", type=float, default=10.0,
        help="Timeout per plugin in seconds",
    )
    test_parser.add_argument(
        "--output", "-o", type=Path,
        help="Save results to JSON file",
    )

    # --- score ---
    score_parser = subparsers.add_parser("score", help="Compute Fossil Score for a tool")
    score_parser.add_argument(
        "--tool", "-t", default="unknown",
        help="Name of the tool",
    )
    score_parser.add_argument(
        "--version", "-v", default="", dest="tool_version",
        help="Version of the tool",
    )
    score_parser.add_argument(
        "--results-file", "-r", type=Path,
        help="Load previous test results instead of running new tests",
    )
    score_parser.add_argument(
        "--output", "-o", type=Path,
        help="Save score to JSON file",
    )
    score_parser.add_argument(
        "--timeout", type=float, default=10.0,
        help="Timeout per plugin in seconds",
    )

    # --- generate ---
    gen_parser = subparsers.add_parser("generate", help="Generate Living Fossils")
    gen_parser.add_argument(
        "--category", "-c",
        choices=[c.value for c in StressCategory],
        help="Generate for a specific stress category",
    )
    gen_parser.add_argument(
        "--count", "-n", type=int, default=10,
        help="Number of test cases to generate",
    )
    gen_parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )
    gen_parser.add_argument(
        "--output", "-o", type=Path,
        help="Save generated programs to JSON file",
    )

    # --- compare ---
    cmp_parser = subparsers.add_parser("compare", help="Compare tool robustness")
    cmp_parser.add_argument(
        "score_a", type=Path,
        help="First score file (JSON)",
    )
    cmp_parser.add_argument(
        "score_b", type=Path,
        help="Second score file (JSON)",
    )

    # --- leaderboard ---
    lb_parser = subparsers.add_parser("leaderboard", help="Show tool leaderboard")
    lb_parser.add_argument(
        "score_files", nargs="*", type=Path,
        help="Score files (JSON) to include in leaderboard",
    )

    # --- corpus ---
    corpus_parser = subparsers.add_parser("corpus", help="Browse the esolang corpus")
    corpus_parser.add_argument(
        "--language", "-l",
        help="Filter by language name",
    )
    corpus_parser.add_argument(
        "--category", "-c",
        choices=[c.value for c in StressCategory],
        help="Filter by stress category",
    )
    corpus_parser.add_argument(
        "--list-languages", action="store_true",
        help="List all languages in the corpus",
    )
    corpus_parser.add_argument(
        "--list-categories", action="store_true",
        help="List all stress categories",
    )

    return parser


def cmd_test(args: argparse.Namespace) -> int:
    """Run the stress test suite."""
    categories = None
    if args.category:
        categories = [StressCategory(c) for c in args.category]

    runner = HarnessRunner(
        plugins=[
            ParserPlugin(timeout=args.timeout),
            LinterPlugin(timeout=args.timeout),
            FormatterPlugin(timeout=args.timeout),
            AIPlugin(timeout=args.timeout),
        ],
        timeout=args.timeout,
    )

    suite_result = runner.run(
        languages=args.language,
        categories=categories,
        min_difficulty=args.min_difficulty,
        max_difficulty=args.max_difficulty,
    )

    # Print summary
    summary = suite_result.summary()
    print(f"=== FossilRecord Test Results ===")
    print(f"Programs tested: {summary['total_programs']}")
    print(f"Parse rate:      {summary['parse_rate']:.1%}")
    print(f"Analysis accuracy: {summary['analysis_accuracy']:.1%}")
    print(f"Crash resistance: {summary['crash_resistance']:.1%}")
    print(f"Memory efficiency: {summary['memory_efficiency']:.1%}")
    print(f"AI comprehension: {summary['ai_rate']:.1%}")
    print(f"Total time:      {summary['total_time_seconds']:.2f}s")

    if args.output:
        suite_result.save(args.output)
        print(f"\nResults saved to {args.output}")

    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Compute the Fossil Score."""
    if args.results_file:
        suite_result = TestSuiteResult.load(args.results_file)
    else:
        runner = HarnessRunner(timeout=args.timeout)
        suite_result = runner.run()

    score = compute_fossil_score(
        suite_result,
        tool_name=args.tool,
        version=args.tool_version,
    )

    print(f"=== Fossil Score: {score.tool_name} ===")
    print(f"Overall Score: {score.score:.1f}/100")
    print(f"\nComponent Breakdown:")
    for comp, val in score.breakdown.components.items():
        weight = score.breakdown.weights.get(comp, 0)
        print(f"  {comp:25s}: {val:.1%} (weight: {weight})")

    if score.breakdown.category_scores:
        print(f"\nCategory Scores:")
        for cat, val in score.breakdown.category_scores.items():
            print(f"  {cat:25s}: {val:.1f}/100")

    if args.output:
        score.save(args.output)
        print(f"\nScore saved to {args.output}")

    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate Living Fossil test cases."""
    config = GenerationConfig(
        count=args.count,
        seed=args.seed,
    )

    generator = LivingFossilGenerator(config=config)

    if args.category:
        programs = generator.generate_for_category(
            StressCategory(args.category), count=args.count
        )
    else:
        programs = generator.generate()

    print(f"=== Generated {len(programs)} Living Fossils ===")
    for prog in programs[:20]:  # Show first 20
        print(f"  {prog.name}: {prog.embedding_type} in {prog.host_language}")

    if len(programs) > 20:
        print(f"  ... and {len(programs) - 20} more")

    if args.output:
        data = {
            "count": len(programs),
            "programs": [p.to_dict() for p in programs],
        }
        args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nSaved to {args.output}")

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two tool scores."""
    score_a = FossilScore.load(args.score_a)
    score_b = FossilScore.load(args.score_b)

    result = ToolComparator.compare(score_a, score_b)

    print(f"=== Tool Comparison ===")
    print(f"{result.tool_a_name}: {result.score_a:.1f}")
    print(f"{result.tool_b_name}: {result.score_b:.1f}")
    print(f"Winner: {result.winner.upper()}")
    print(f"Difference: {abs(result.score_diff):.1f} points")

    if result.component_diffs:
        print(f"\nComponent Differences (A - B):")
        for comp, diff in result.component_diffs.items():
            sign = "+" if diff > 0 else ""
            print(f"  {comp:25s}: {sign}{diff:.4f}")

    return 0


def cmd_leaderboard(args: argparse.Namespace) -> int:
    """Show the tool leaderboard."""
    scores = []
    for path in args.score_files:
        try:
            scores.append(FossilScore.load(path))
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}", file=sys.stderr)

    if not scores:
        print("No score files provided. Usage: fossil leaderboard score1.json score2.json ...")
        return 1

    board = ToolComparator.leaderboard(scores)
    print("=== Fossil Score Leaderboard ===")
    print(f"{'Rank':<5} {'Tool':<20} {'Version':<10} {'Score':<10}")
    print("-" * 50)
    for i, entry in enumerate(board, 1):
        print(f"{i:<5} {entry['tool_name']:<20} {entry['version']:<10} {entry['fossil_score']:<10.1f}")

    return 0


def cmd_corpus(args: argparse.Namespace) -> int:
    """Browse the esolang corpus."""
    loader = CorpusLoader()
    programs = loader.programs()

    if args.list_languages:
        langs = loader.languages()
        print(f"=== Languages in Corpus ({len(langs)}) ===")
        for lang in sorted(langs):
            count = len(loader.by_language(lang))
            print(f"  {lang}: {count} program(s)")
        return 0

    if args.list_categories:
        cats = loader.categories()
        print(f"=== Stress Categories ({len(cats)}) ===")
        for cat in sorted(cats, key=lambda c: c.value):
            count = len(loader.by_category(cat))
            print(f"  {cat.value}: {count} program(s)")
        return 0

    # Apply filters
    if args.language:
        programs = loader.by_language(args.language)
    if args.category:
        programs = [p for p in programs if StressCategory(args.category) in p.categories]

    print(f"=== Esolang Corpus ({len(programs)} programs) ===")
    for prog in programs:
        cats = ", ".join(c.value for c in prog.categories)
        print(f"  [{prog.language}] {prog.name} (difficulty: {prog.difficulty}, categories: {cats})")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the fossil CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "test": cmd_test,
        "score": cmd_score,
        "generate": cmd_generate,
        "compare": cmd_compare,
        "leaderboard": cmd_leaderboard,
        "corpus": cmd_corpus,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
