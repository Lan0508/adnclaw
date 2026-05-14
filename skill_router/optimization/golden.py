"""Golden Cases management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from skill_router.core.schema import GoldenCase, parse_golden


def load_golden(path: Path) -> List[GoldenCase]:
    cases = []
    if not path.exists():
        return cases
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"line {line_no}: invalid JSON: {e}") from e
            cases.append(parse_golden(raw, line_no))
    return cases


def add_golden(path: Path, case: GoldenCase) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    need_newline = False
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            content = f.read()
            if content and not content.endswith("\n"):
                need_newline = True
    with path.open("a", encoding="utf-8") as f:
        if need_newline:
            f.write("\n")
        data = {
            "id": case.id,
            "query": case.query,
            "correct_skill": case.correct_skill,
            "context": case.context,
        }
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def validate_new_case(path: Path, case: GoldenCase) -> bool:
    existing = load_golden(path)
    ids = {c.id for c in existing}
    queries = {c.query for c in existing}
    if case.id in ids:
        return False
    if case.query in queries:
        return False
    return True