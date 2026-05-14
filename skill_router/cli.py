"""CLI: build | query | wrap | eval | diagnose | suggest | tune | golden."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_router.retrieval import run_build, TOP_K, run_query, run_wrap, BM25Index, get_bm25_path
from skill_router.optimization import run_eval, format_report, save_report, run_diagnose, format_diagnoses, generate_suggestions, format_suggestions, save_suggestions, find_optimal_threshold, format_tune_result, load_golden, add_golden, validate_new_case
from skill_router.core import GoldenCase, record_to_chroma_metadata, DEFAULT_DISTANCE_THRESHOLD, get_client, COLLECTION_NAME, Embedder

GOLDEN_DEFAULT = Path("data/golden_cases.jsonl")
SUGGESTIONS_DEFAULT = Path("data/suggestions.jsonl")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="skill_router",
        description="Local scenario RAG with evaluation feedback loop.",
    )
    parser.add_argument(
        "--chroma-dir",
        default="chroma_data",
        help="Chroma persistence directory (default: ./chroma_data)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="sentence-transformers model id",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Index JSONL scenarios into Chroma")
    p_build.add_argument("--input", required=True, type=Path, help="Path to JSONL scenarios")
    p_build.add_argument("--reset", action="store_true", help="Delete existing collection before re-indexing")

    p_query = sub.add_parser("query", help=f"Print routing hints (Top-{TOP_K})")
    p_query.add_argument("--question", required=True, help="User question text")
    p_query.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD, help="Max distance threshold")
    p_query.add_argument("--hybrid", action="store_true", help="Enable hybrid search (vector + BM25)")

    p_wrap = sub.add_parser("wrap", help="Print hints + user message")
    p_wrap.add_argument("--question", default=None, help="User message (or read stdin)")
    p_wrap.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    p_wrap.add_argument("--hybrid", action="store_true")

    p_eval = sub.add_parser("eval", help="Evaluate against golden cases")
    p_eval.add_argument("--golden", type=Path, default=GOLDEN_DEFAULT, help="Path to golden cases JSONL")
    p_eval.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    p_eval.add_argument("--hybrid", action="store_true")
    p_eval.add_argument("--save", type=Path, default=None, help="Save report to JSON file")

    p_diagnose = sub.add_parser("diagnose", help="Diagnose failed golden cases")
    p_diagnose.add_argument("--golden", type=Path, default=GOLDEN_DEFAULT)
    p_diagnose.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    p_diagnose.add_argument("--hybrid", action="store_true")

    p_suggest = sub.add_parser("suggest", help="Generate optimization suggestions")
    p_suggest.add_argument("--golden", type=Path, default=GOLDEN_DEFAULT)
    p_suggest.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    p_suggest.add_argument("--hybrid", action="store_true")
    p_suggest.add_argument("--save", type=Path, default=SUGGESTIONS_DEFAULT, help="Save suggestions to JSONL")
    p_suggest.add_argument("--apply", action="store_true", help="Auto-apply suggestions to scenarios")

    p_tune = sub.add_parser("tune", help="Auto-tune threshold for best hit rate")
    p_tune.add_argument("--golden", type=Path, default=GOLDEN_DEFAULT)
    p_tune.add_argument("--hybrid", action="store_true")
    p_tune.add_argument("--min", type=float, default=0.5, help="Min threshold to search")
    p_tune.add_argument("--max", type=float, default=2.0, help="Max threshold to search")
    p_tune.add_argument("--step", type=float, default=0.1, help="Search step")

    p_golden = sub.add_parser("golden", help="Manage golden cases")
    p_golden.add_argument("--golden", type=Path, default=GOLDEN_DEFAULT)
    p_golden_sub = p_golden.add_subparsers(dest="golden_cmd", required=True)

    p_golden_add = p_golden_sub.add_parser("add", help="Add new golden case")
    p_golden_add.add_argument("--id", required=True, help="Case ID")
    p_golden_add.add_argument("--query", required=True, help="User query")
    p_golden_add.add_argument("--skill", required=True, help="Correct skill_view_name")
    p_golden_add.add_argument("--context", default="", help="Additional context")

    p_golden_list = p_golden_sub.add_parser("list", help="List golden cases")

    args = parser.parse_args(argv)
    chroma_dir = Path(args.chroma_dir).resolve()

    if args.command == "build":
        return run_build(args.input.resolve(), chroma_dir, reset=args.reset, model_name=args.model)

    if args.command == "query":
        print(run_query(args.question, chroma_dir, model_name=args.model, threshold=args.threshold, hybrid=args.hybrid))
        return 0

    if args.command == "wrap":
        return run_wrap(args.question, chroma_dir, model_name=args.model, threshold=args.threshold, hybrid=args.hybrid)

    if args.command == "eval":
        report = run_eval(args.golden, chroma_dir, args.threshold, args.hybrid)
        print(format_report(report))
        if args.save:
            save_report(report, args.save)
            print(f"\nReport saved to: {args.save}")
        return 0

    if args.command == "diagnose":
        report = run_eval(args.golden, chroma_dir, args.threshold, args.hybrid)
        diagnoses = run_diagnose(report.results, chroma_dir, args.threshold)
        print(format_diagnoses(diagnoses))
        return 0

    if args.command == "suggest":
        report = run_eval(args.golden, chroma_dir, args.threshold, args.hybrid)
        diagnoses = run_diagnose(report.results, chroma_dir, args.threshold)
        suggestions = generate_suggestions(diagnoses, args.golden)
        print(format_suggestions(suggestions))
        save_suggestions(suggestions, args.save)
        print(f"\nSuggestions saved to: {args.save}")
        if args.apply and suggestions:
            embedder = Embedder(model_name=args.model)
            texts = [s.text for s in suggestions]
            embeddings = embedder.encode(texts)
            ids = [s.id for s in suggestions]
            metadatas = [record_to_chroma_metadata(s) for s in suggestions]

            client = get_client(str(chroma_dir))
            collection = client.get_or_create_collection(name=COLLECTION_NAME)
            collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

            bm25_path = get_bm25_path(chroma_dir)
            bm25_index = BM25Index.load(bm25_path)
            for s in suggestions:
                bm25_index.add(s.id, s.text)
            bm25_index.build()
            bm25_index.save(bm25_path)

            print(f"Applied {len(suggestions)} suggestions to index")
        return 0

    if args.command == "tune":
        threshold, report = find_optimal_threshold(
            args.golden, chroma_dir, args.hybrid,
            min_threshold=args.min, max_threshold=args.max, step=args.step,
        )
        print(format_tune_result(threshold, report))
        return 0

    if args.command == "golden":
        golden_path = args.golden
        if args.golden_cmd == "add":
            case = GoldenCase(
                id=args.id,
                query=args.query,
                correct_skill=args.skill,
                context=args.context,
            )
            if not validate_new_case(golden_path, case):
                print(f"Error: duplicate id or query in {golden_path}", file=sys.stderr)
                return 1
            add_golden(golden_path, case)
            print(f"Added golden case: {case.id}")
            return 0

        if args.golden_cmd == "list":
            cases = load_golden(golden_path)
            for c in cases:
                print(f"{c.id}: '{c.query}' → {c.correct_skill}")
            return 0

    return 2