"""CLI for Curator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ussy_curator.catalog import MARCRecord
from ussy_curator.classification import classify_document, FacetedClassification
from ussy_curator.conservation import ConservationReport
from ussy_curator.exhibition import Exhibition
from ussy_curator.models import Document
from ussy_curator.provenance import ProvenanceTracker
from ussy_curator.storage import Storage
from ussy_curator.utils import parse_yaml_frontmatter, vectorize
from ussy_curator.weeding import WeedingEngine


def _build_document(path: Path) -> Document:
    """Build a fully-instrumented Document from a path."""
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    doc = Document(path=path, content=content)

    # Attach instruments
    doc.marc_record = MARCRecord(path)
    doc.accession_number = doc.marc_record.fields.get("260", {}).get("c", "")

    content_analysis = {
        "tf": vectorize(content),
        "readability": 50.0,
        "jargon_density": 0.1,
        "named_entities": doc.keywords[:3],
        "concept_depth": 0.5,
    }
    doc.classification = classify_document(path, content_analysis)
    doc.conservation_report = ConservationReport(path)

    db = Storage()
    db.initialize()
    tracker = ProvenanceTracker(db)
    if not db.get_accession(path):
        tracker.accession(path)
    doc.provenance_chain = tracker.build_provenance_chain(path)

    return doc


def _build_collection(paths: list[Path]) -> list[Document]:
    """Build a collection of fully-instrumented Documents."""
    docs = [_build_document(p) for p in paths if p.exists()]
    # Wire backlinks
    path_map = {d.path: d for d in docs}
    from ussy_curator.utils import extract_markdown_links
    for doc in docs:
        doc.backlinks = [
            link.source for link in extract_markdown_links(doc.path)
            if link.source in path_map
        ]
    return docs


def cmd_catalog(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"Error: path not found: {path}", file=sys.stderr)
        return 1
    record = MARCRecord(path)
    print(f"MARC Record for {path}")
    print(f"  Completeness Score: {record.completeness_score():.3f}")
    for code, value in record.fields.items():
        print(f"  {code} ({record.FIELD_MAP.get(code, '?')}): {value}")
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"Error: path not found: {path}", file=sys.stderr)
        return 1
    content = path.read_text(encoding="utf-8")
    analysis = {
        "tf": vectorize(content),
        "readability": 50.0,
        "jargon_density": 0.1,
        "named_entities": [],
        "concept_depth": 0.5,
    }
    fc = classify_document(path, analysis)
    print(f"Classification for {path}")
    print(f"  Notation: {fc.notation}")
    print(f"  Hierarchy: {fc.hierarchy}")
    print(f"  Facets: {fc.facets}")
    print(f"  Broader Terms: {fc.broader_terms()}")
    print(f"  Narrower Term Space: {fc.narrower_term_space()}")
    return 0


def cmd_condition(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"Error: path not found: {path}", file=sys.stderr)
        return 1
    report = ConservationReport(path)
    print(f"Conservation Report for {path}")
    print(f"  Condition Index: {report.condition_index():.2f}")
    print(f"  Grade: {report.grade()}")
    print(f"  Deterioration Rate: {report.deterioration_rate():.6f}")
    print(f"  Treatment: {report.recommended_treatment()}")
    print(f"  Metrics: {report.metrics}")
    return 0


def cmd_provenance(args: argparse.Namespace) -> int:
    path = Path(args.path)
    db = Storage()
    db.initialize()
    tracker = ProvenanceTracker(db)
    if not db.get_accession(path):
        tracker.accession(path)
    chain = tracker.build_provenance_chain(path)
    print(f"Provenance for {path}")
    print(f"  Accession Number: {chain['accession_number']}")
    print(f"  Completeness: {chain['completeness']:.3f}")
    print(f"  Gaps: {len(chain['gaps'])}")
    for link in chain["chain"]:
        print(f"    {link['event_type']} by {link['custodian']} on {link['date']} (confidence: {link['confidence']:.2f})")
    return 0


def cmd_exhibit(args: argparse.Namespace) -> int:
    target = Path(args.target) if getattr(args, "target", None) else Path(".")
    if target.is_dir():
        paths = list(target.rglob("*.md"))
    else:
        paths = [target]
    collection = _build_collection(paths)
    if not collection:
        print("No documents found.")
        return 0
    audience_profile = {"level": args.audience}
    exhibition = Exhibition(args.theme, args.theme, audience_profile, max_items=args.max_items)
    exhibition.curate(collection)
    print(f"Exhibition: {exhibition.name}")
    print(f"  Theme: {exhibition.theme}")
    print(f"  Audience: {exhibition.audience}")
    print(f"  Selected {len(exhibition.selection)} documents:")
    for doc in exhibition.selection:
        label = exhibition.didactic_label(doc)
        print(f"    - {doc.path.name}: {label}")
    return 0


def cmd_weed(args: argparse.Namespace) -> int:
    target = Path(args.target) if getattr(args, "target", None) else Path(".")
    if target.is_dir():
        paths = list(target.rglob("*.md"))
    else:
        paths = [target]
    collection = _build_collection(paths)
    if not collection:
        print("No documents found.")
        return 0
    engine = WeedingEngine()
    candidates = engine.batch_weed(collection, threshold=args.threshold)
    print(f"Weeding Report ({len(candidates)} candidates above threshold {args.threshold})")
    for prop in candidates:
        print(f"  {prop['title']} ({prop['accession_number']}): score {prop['weed_score']}")
        print(f"    Triggered: {', '.join(prop['triggered_criteria'])}")
        print(f"    Disposition: {prop['disposition']}")
        if args.dry_run:
            print(f"    [dry-run] would propose deaccession")
    return 0


def cmd_shelf(args: argparse.Namespace) -> int:
    target = Path(args.target) if getattr(args, "target", None) else Path(".")
    if target.is_dir():
        paths = list(target.rglob("*.md"))
    else:
        paths = [target]
    facet_filter = getattr(args, "facet", None)
    docs = []
    for p in paths:
        content = p.read_text(encoding="utf-8") if p.exists() else ""
        analysis = {
            "tf": vectorize(content),
            "readability": 50.0,
            "jargon_density": 0.1,
            "named_entities": [],
            "concept_depth": 0.5,
        }
        fc = classify_document(p, analysis)
        if facet_filter:
            key, _, val = facet_filter.partition(":")
            if fc.facets.get(key) != val:
                continue
        docs.append((fc, p))
    docs.sort(key=lambda x: x[0].notation)
    print("Shelf Browse")
    for fc, p in docs:
        print(f"  {fc.notation}  {p}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    target = Path(args.target) if getattr(args, "target", None) else Path(".")
    if target.is_dir():
        paths = list(target.rglob("*.md"))
    else:
        paths = [target]
    collection = _build_collection(paths)
    if not collection:
        print("No documents found.")
        return 0

    total_completeness = sum(d.marc_record.completeness_score() for d in collection)
    avg_completeness = total_completeness / len(collection) if collection else 0.0
    total_condition = sum(d.conservation_report.condition_index() for d in collection)
    avg_condition = total_condition / len(collection) if collection else 0.0

    engine = WeedingEngine()
    candidates = engine.batch_weed(collection)

    report = {
        "document_count": len(collection),
        "avg_catalog_completeness": round(avg_completeness, 3),
        "avg_condition_index": round(avg_condition, 2),
        "deaccession_candidates": len(candidates),
        "documents": [
            {
                "path": str(d.path),
                "completeness": round(d.marc_record.completeness_score(), 3),
                "condition": round(d.conservation_report.condition_index(), 2),
                "grade": d.conservation_report.grade(),
                "accession": d.accession_number,
            }
            for d in collection
        ],
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Collection Health Audit")
        print(f"  Documents: {report['document_count']}")
        print(f"  Avg Catalog Completeness: {report['avg_catalog_completeness']}")
        print(f"  Avg Condition Index: {report['avg_condition_index']}")
        print(f"  Deaccession Candidates: {report['deaccession_candidates']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="curator",
        description="Library science for documentation health",
    )
    subparsers = parser.add_subparsers(dest="command")

    # catalog
    p_catalog = subparsers.add_parser("catalog", help="Generate MARC record")
    p_catalog.add_argument("path", help="Path to document")
    p_catalog.set_defaults(func=cmd_catalog)

    # classify
    p_classify = subparsers.add_parser("classify", help="Assign classification")
    p_classify.add_argument("path", help="Path to document")
    p_classify.set_defaults(func=cmd_classify)

    # condition
    p_condition = subparsers.add_parser("condition", help="Generate conservation report")
    p_condition.add_argument("path", help="Path to document")
    p_condition.set_defaults(func=cmd_condition)

    # provenance
    p_provenance = subparsers.add_parser("provenance", help="Display provenance chain")
    p_provenance.add_argument("path", help="Path to document")
    p_provenance.set_defaults(func=cmd_provenance)

    # exhibit
    p_exhibit = subparsers.add_parser("exhibit", help="Curate contextual view")
    p_exhibit.add_argument("--theme", default="general", help="Exhibition theme")
    p_exhibit.add_argument("--audience", default="general", help="Target audience level")
    p_exhibit.add_argument("--max-items", type=int, default=20, help="Maximum items")
    p_exhibit.add_argument("--target", default=".", help="Target directory or file")
    p_exhibit.set_defaults(func=cmd_exhibit)

    # weed
    p_weed = subparsers.add_parser("weed", help="Identify deaccession candidates")
    p_weed.add_argument("--threshold", type=float, default=0.6, help="Weeding threshold")
    p_weed.add_argument("--dry-run", action="store_true", help="Dry run")
    p_weed.add_argument("--target", default=".", help="Target directory or file")
    p_weed.set_defaults(func=cmd_weed)

    # shelf
    p_shelf = subparsers.add_parser("shelf", help="Browse by classification")
    p_shelf.add_argument("--facet", default=None, help="Facet filter (e.g., AUD:expert)")
    p_shelf.add_argument("--target", default=".", help="Target directory")
    p_shelf.set_defaults(func=cmd_shelf)

    # audit
    p_audit = subparsers.add_parser("audit", help="Full collection health report")
    p_audit.add_argument("--json", action="store_true", help="Output JSON")
    p_audit.add_argument("--target", default=".", help="Target directory")
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
