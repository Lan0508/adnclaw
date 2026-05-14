"""CLI: build | query | wrap."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_router.build import run_build
from skill_router.query import TOP_K, run_query
from skill_router.wrap_cmd import run_wrap


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="skill_router",
        description="Local scenario RAG → Hermes skill_view routing hints (Top-K=3).",
    )
    parser.add_argument(
        "--chroma-dir",
        default="chroma_data",
        help="Chroma persistence directory (default: ./chroma_data)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="sentence-transformers model id (default: env SKILL_ROUTER_MODEL or all-MiniLM-L6-v2)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Index JSONL scenarios into Chroma")
    p_build.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSONL (one scenario object per line)",
    )
    p_build.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before re-indexing",
    )

    p_query = sub.add_parser("query", help=f"Print routing hints for a question (Top-{TOP_K})")
    p_query.add_argument("--question", required=True, help="User question text")

    p_wrap = sub.add_parser(
        "wrap",
        help="Print hints + blank line + user message (stdin or --question)",
    )
    p_wrap.add_argument(
        "--question",
        default=None,
        help="User message; if omitted, read entire stdin",
    )

    args = parser.parse_args(argv)
    chroma_dir = Path(args.chroma_dir).resolve()

    if args.command == "build":
        return run_build(
            args.input.resolve(),
            chroma_dir,
            reset=args.reset,
            model_name=args.model,
        )

    if args.command == "query":
        out = run_query(args.question, chroma_dir, model_name=args.model)
        print(out)
        return 0

    if args.command == "wrap":
        return run_wrap(args.question, chroma_dir, model_name=args.model)

    return 2
