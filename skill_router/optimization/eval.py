"""Batch evaluation against golden cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from skill_router.optimization.golden import load_golden
from skill_router.retrieval.query import run_query


@dataclass
class EvalResult:
    golden_id: str
    query: str
    correct_skill: str
    hints: List[str]
    hit_top1: bool
    hit_top3: bool
    skipped: bool
    distance: float


@dataclass
class EvalReport:
    timestamp: str
    total_cases: int
    hit_top1_count: int
    hit_top3_count: int
    skipped_count: int
    miss_count: int
    hit_top1_rate: float
    hit_top3_rate: float
    skip_rate: float
    avg_distance: float
    results: List[EvalResult]


def evaluate_single(case, chroma_dir: Path, threshold: float, hybrid: bool) -> EvalResult:
    hints_text = run_query(
        case.query,
        chroma_dir,
        model_name=None,
        threshold=threshold,
        hybrid=hybrid,
    )
    hints = extract_skills_from_hints(hints_text)
    hit_top1 = len(hints) > 0 and hints[0] == case.correct_skill
    hit_top3 = case.correct_skill in hints[:3]
    skipped = len(hints) == 0
    return EvalResult(
        golden_id=case.id,
        query=case.query,
        correct_skill=case.correct_skill,
        hints=hints,
        hit_top1=hit_top1,
        hit_top3=hit_top3,
        skipped=skipped,
        distance=0.0,
    )


def extract_skills_from_hints(hints_text: str) -> List[str]:
    skills = []
    for line in hints_text.split("\n"):
        if "skill_view(name=" in line:
            start = line.find("skill_view(name='") + len("skill_view(name='")
            end = line.find("')", start)
            if start > 0 and end > start:
                skills.append(line[start:end])
    return skills


def run_eval(
    golden_path: Path,
    chroma_dir: Path,
    threshold: float,
    hybrid: bool,
) -> EvalReport:
    cases = load_golden(golden_path)
    results = []
    total_distance = 0.0
    distance_count = 0

    for case in cases:
        r = evaluate_single(case, chroma_dir, threshold, hybrid)
        results.append(r)
        if not r.skipped and r.distance > 0:
            total_distance += r.distance
            distance_count += 1

    total = len(cases)
    hit_top1 = sum(1 for r in results if r.hit_top1)
    hit_top3 = sum(1 for r in results if r.hit_top3)
    skipped = sum(1 for r in results if r.skipped)
    miss = total - hit_top3

    avg_dist = total_distance / distance_count if distance_count > 0 else 0.0

    return EvalReport(
        timestamp=datetime.now().isoformat(),
        total_cases=total,
        hit_top1_count=hit_top1,
        hit_top3_count=hit_top3,
        skipped_count=skipped,
        miss_count=miss,
        hit_top1_rate=hit_top1 / total if total > 0 else 0.0,
        hit_top3_rate=hit_top3 / total if total > 0 else 0.0,
        skip_rate=skipped / total if total > 0 else 0.0,
        avg_distance=avg_dist,
        results=results,
    )


def format_report(report: EvalReport) -> str:
    lines = [
        f"=== Evaluation Report ({report.timestamp}) ===",
        f"Total Cases: {report.total_cases}",
        f"Hit Top-1: {report.hit_top1_count} ({report.hit_top1_rate:.1%})",
        f"Hit Top-3: {report.hit_top3_count} ({report.hit_top3_rate:.1%})",
        f"Skipped: {report.skipped_count} ({report.skip_rate:.1%})",
        f"Miss: {report.miss_count}",
        "",
        "Details:",
    ]
    for r in report.results:
        status = "✓ Top-1" if r.hit_top1 else ("✓ Top-3" if r.hit_top3 else ("⊘ Skip" if r.skipped else "✗ Miss"))
        lines.append(f"  [{status}] {r.golden_id}: '{r.query}' → {r.correct_skill}")
        if r.hints:
            lines.append(f"    Hints: {', '.join(r.hints[:3])}")
    return "\n".join(lines)


def save_report(report: EvalReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": report.timestamp,
        "total_cases": report.total_cases,
        "hit_top1_count": report.hit_top1_count,
        "hit_top3_count": report.hit_top3_count,
        "skipped_count": report.skipped_count,
        "miss_count": report.miss_count,
        "hit_top1_rate": report.hit_top1_rate,
        "hit_top3_rate": report.hit_top3_rate,
        "skip_rate": report.skip_rate,
        "avg_distance": report.avg_distance,
        "results": [
            {
                "golden_id": r.golden_id,
                "query": r.query,
                "correct_skill": r.correct_skill,
                "hints": r.hints,
                "hit_top1": r.hit_top1,
                "hit_top3": r.hit_top3,
                "skipped": r.skipped,
            }
            for r in report.results
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)