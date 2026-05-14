"""Prepend routing hints to user message (stdin or --question)."""

from __future__ import annotations

import sys

from skill_router.retrieval.query import run_query
from skill_router.core.store import DEFAULT_DISTANCE_THRESHOLD


def run_wrap(
    question: str | None,
    chroma_dir,
    model_name: str | None,
    threshold: float | None = None,
    hybrid: bool = False,
) -> int:
    if question is not None and str(question).strip():
        user = str(question).strip()
    else:
        user = sys.stdin.read()
        user = user.strip()

    if not user:
        print("wrap: empty user message (use --question or pipe stdin).", file=sys.stderr)
        return 1

    hints = run_query(
        user,
        chroma_dir,
        model_name=model_name,
        threshold=threshold,
        hybrid=hybrid,
    )
    print(f"{hints}\n\n{user}")
    return 0
