"""Diagnose why golden cases fail."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from skill_router.optimization.eval import EvalResult
from skill_router.optimization.golden import load_golden
from skill_router.core.schema import ScenarioRecord
from skill_router.core.store import get_collection


@dataclass
class Diagnosis:
    golden_id: str
    query: str
    correct_skill: str
    problem_type: str
    details: str
    suggestion: str


PROBLEM_TYPES = {
    "skill_not_in_scenarios": "Correct skill not in scenario database",
    "threshold_too_strict": "Results filtered by threshold",
    "wrong_skill_ranked_higher": "Incorrect skill ranked higher than correct one",
    "no_match": "No similar scenarios found",
}


def get_all_skills_in_scenarios(chroma_dir: Path) -> set:
    collection = get_collection(str(chroma_dir))
    result = collection.get(include=["metadatas"])
    metas = result.get("metadatas") or []
    skills = set()
    for m in metas:
        if isinstance(m, dict):
            skill = m.get("skill_view_name")
            if skill:
                skills.add(skill)
    return skills


def diagnose_result(
    result: EvalResult,
    chroma_dir: Path,
    threshold: float,
) -> Diagnosis:
    skills_in_db = get_all_skills_in_scenarios(chroma_dir)

    if result.correct_skill not in skills_in_db:
        return Diagnosis(
            golden_id=result.golden_id,
            query=result.query,
            correct_skill=result.correct_skill,
            problem_type="skill_not_in_scenarios",
            details=f"Skill '{result.correct_skill}' not found in scenario database",
            suggestion="Add scenario for this skill using: skill_router suggest --golden-id {result.golden_id}",
        )

    if result.skipped:
        return Diagnosis(
            golden_id=result.golden_id,
            query=result.query,
            correct_skill=result.correct_skill,
            problem_type="threshold_too_strict",
            details=f"Query matched scenarios but filtered by threshold={threshold}",
            suggestion="Try higher threshold or add more specific scenario text",
        )

    if not result.hit_top3 and result.hints:
        return Diagnosis(
            golden_id=result.golden_id,
            query=result.query,
            correct_skill=result.correct_skill,
            problem_type="wrong_skill_ranked_higher",
            details=f"Returned: {result.hints[:3]}, expected: {result.correct_skill}",
            suggestion="Improve scenario text or add negative samples for wrong skills",
        )

    return Diagnosis(
        golden_id=result.golden_id,
        query=result.query,
        correct_skill=result.correct_skill,
        problem_type="no_match",
        details="No scenarios matched query",
        suggestion="Add scenario with similar query text",
    )


def run_diagnose(
    results: List[EvalResult],
    chroma_dir: Path,
    threshold: float,
) -> List[Diagnosis]:
    diagnoses = []
    for r in results:
        if r.hit_top1:
            continue
        diagnoses.append(diagnose_result(r, chroma_dir, threshold))
    return diagnoses


def format_diagnoses(diagnoses: List[Diagnosis]) -> str:
    lines = ["=== Diagnosis Report ===", ""]
    by_type = {}
    for d in diagnoses:
        by_type.setdefault(d.problem_type, []).append(d)

    for ptype, items in by_type.items():
        lines.append(f"## {ptype} ({len(items)} cases)")
        for d in items:
            lines.append(f"  - [{d.golden_id}] '{d.query}' → {d.correct_skill}")
            lines.append(f"    Problem: {d.details}")
            lines.append(f"    Suggestion: {d.suggestion}")
        lines.append("")
    return "\n".join(lines)