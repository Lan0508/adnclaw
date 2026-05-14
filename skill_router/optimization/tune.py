"""Auto-tune threshold based on golden cases."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from skill_router.optimization.eval import EvalReport, run_eval
from skill_router.optimization.golden import load_golden


def find_optimal_threshold(
    golden_path: Path,
    chroma_dir: Path,
    hybrid: bool,
    min_threshold: float = 0.5,
    max_threshold: float = 2.0,
    step: float = 0.1,
) -> Tuple[float, EvalReport]:
    best_threshold = max_threshold
    best_hit_rate = 0.0
    best_report = None

    threshold = min_threshold
    while threshold <= max_threshold:
        report = run_eval(golden_path, chroma_dir, threshold, hybrid)
        hit_rate = report.hit_top3_rate
        if hit_rate > best_hit_rate:
            best_hit_rate = hit_rate
            best_threshold = threshold
            best_report = report
        threshold += step

    return best_threshold, best_report


def format_tune_result(threshold: float, report: EvalReport) -> str:
    lines = [
        f"=== Threshold Tuning Result ===",
        f"Optimal threshold: {threshold:.2f}",
        f"Hit Top-3 rate: {report.hit_top3_rate:.1%}",
        f"Skip rate: {report.skip_rate:.1%}",
        "",
        "Recommendation:",
        f"  Use --threshold {threshold:.2f} for best results",
    ]
    return "\n".join(lines)