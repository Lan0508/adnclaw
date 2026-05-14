"""Prepend routing hints to user message (stdin or --question)."""

from __future__ import annotations

import sys

from skill_router.query import run_query


def run_wrap(question: str | None, chroma_dir, model_name: str | None) -> int:
    if question is not None and str(question).strip():
        user = str(question).strip()
    else:
        user = sys.stdin.read()
        user = user.strip()

    if not user:
        print("wrap: empty user message (use --question or pipe stdin).", file=sys.stderr)
        return 1

    hints = run_query(user, chroma_dir, model_name=model_name)
    print(f"{hints}\n\n{user}")
    return 0
