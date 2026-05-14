"""Generate optimization suggestions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from skill_router.optimization.diagnose import Diagnosis
from skill_router.optimization.golden import load_golden
from skill_router.core.schema import GoldenCase, ScenarioRecord, golden_to_scenario


def generate_scenario_suggestion(golden: GoldenCase) -> ScenarioRecord:
    return golden_to_scenario(golden)


def generate_negative_suggestion(
    golden: GoldenCase,
    wrong_skills: List[str],
) -> ScenarioRecord:
    rec = golden_to_scenario(golden)
    rec.negative = wrong_skills
    rec.notes = f"Added negatives to prevent wrong routing: {', '.join(wrong_skills)}"
    return rec


def generate_suggestions(
    diagnoses: List[Diagnosis],
    golden_path: Path,
) -> List[ScenarioRecord]:
    goldens = load_golden(golden_path)
    golden_map = {g.id: g for g in goldens}
    suggestions = []

    for d in diagnoses:
        golden = golden_map.get(d.golden_id)
        if not golden:
            continue

        if d.problem_type == "skill_not_in_scenarios":
            suggestions.append(generate_scenario_suggestion(golden))

        elif d.problem_type == "wrong_skill_ranked_higher":
            wrong_skills = [s for s in d.details.split("Returned: ")[1].split(",")[0].strip("[]").split(", ") if s and s != golden.correct_skill]
            if wrong_skills:
                suggestions.append(generate_negative_suggestion(golden, wrong_skills[:3]))

        elif d.problem_type in ("threshold_too_strict", "no_match"):
            suggestions.append(generate_scenario_suggestion(golden))

    return suggestions


def format_suggestions(suggestions: List[ScenarioRecord]) -> str:
    lines = ["=== Optimization Suggestions ===", ""]
    lines.append("Add these scenarios to improve hit rate:")
    lines.append("")
    for s in suggestions:
        data = {
            "id": s.id,
            "text": s.text,
            "skill_view_name": s.skill_view_name,
            "negative": s.negative,
            "notes": s.notes,
        }
        lines.append(json.dumps(data, ensure_ascii=False))
    return "\n".join(lines)


def save_suggestions(suggestions: List[ScenarioRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in suggestions:
            data = {
                "id": s.id,
                "text": s.text,
                "skill_view_name": s.skill_view_name,
                "negative": s.negative,
                "notes": s.notes,
            }
            f.write(json.dumps(data, ensure_ascii=False) + "\n")