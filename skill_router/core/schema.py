"""JSONL scenario records: validation and normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ScenarioRecord:
    id: str
    text: str
    skill_view_name: str
    file_path: Optional[str]
    negative: List[str]
    notes: str


@dataclass
class GoldenCase:
    id: str
    query: str
    correct_skill: str
    context: str


def parse_record(raw: dict[str, Any], line_no: int) -> ScenarioRecord:
    if not isinstance(raw, dict):
        raise ValueError(f"line {line_no}: record must be a JSON object")

    sid = str(raw.get("id", "")).strip()
    if not sid:
        raise ValueError(f"line {line_no}: missing non-empty 'id'")

    text = str(raw.get("text", "")).strip()
    if not text:
        raise ValueError(f"line {line_no}: missing non-empty 'text'")

    svn = str(raw.get("skill_view_name", "")).strip()
    if not svn:
        raise ValueError(f"line {line_no}: missing non-empty 'skill_view_name'")

    fp = raw.get("file_path")
    if fp is None or fp == "":
        file_path: Optional[str] = None
    else:
        file_path = str(fp).strip() or None

    neg = raw.get("negative") or []
    if isinstance(neg, str):
        try:
            neg = json.loads(neg)
        except json.JSONDecodeError:
            neg = [neg]
    if not isinstance(neg, list):
        raise ValueError(f"line {line_no}: 'negative' must be a list or JSON array string")
    negative = [str(x).strip() for x in neg if str(x).strip()]

    notes = str(raw.get("notes", "") or "").strip()

    return ScenarioRecord(
        id=sid,
        text=text,
        skill_view_name=svn,
        file_path=file_path,
        negative=negative,
        notes=notes,
    )


def record_to_chroma_metadata(rec: ScenarioRecord) -> dict[str, str]:
    """Chroma metadata values must be str / int / float / bool."""
    return {
        "skill_view_name": rec.skill_view_name,
        "file_path": rec.file_path or "",
        "negative_json": json.dumps(rec.negative, ensure_ascii=False),
        "notes": rec.notes,
    }


def metadata_to_hit(text: str, meta: dict[str, Any]) -> dict[str, Any]:
    neg_raw = meta.get("negative_json") or "[]"
    try:
        negative = json.loads(neg_raw) if isinstance(neg_raw, str) else list(neg_raw or [])
    except json.JSONDecodeError:
        negative = []
    if not isinstance(negative, list):
        negative = []
    fp = meta.get("file_path") or ""
    return {
        "text": text,
        "skill_view_name": str(meta.get("skill_view_name", "")),
        "file_path": fp.strip() or None,
        "negative": [str(x) for x in negative],
        "notes": str(meta.get("notes", "") or ""),
    }


def parse_golden(raw: dict[str, Any], line_no: int) -> GoldenCase:
    if not isinstance(raw, dict):
        raise ValueError(f"line {line_no}: golden case must be a JSON object")

    gid = str(raw.get("id", "")).strip()
    if not gid:
        raise ValueError(f"line {line_no}: missing non-empty 'id'")

    query = str(raw.get("query", "")).strip()
    if not query:
        raise ValueError(f"line {line_no}: missing non-empty 'query'")

    correct_skill = str(raw.get("correct_skill", "")).strip()
    if not correct_skill:
        raise ValueError(f"line {line_no}: missing non-empty 'correct_skill'")

    context = str(raw.get("context", "") or "").strip()

    return GoldenCase(
        id=gid,
        query=query,
        correct_skill=correct_skill,
        context=context,
    )


def golden_to_scenario(golden: GoldenCase) -> ScenarioRecord:
    return ScenarioRecord(
        id=f"auto-{golden.id}",
        text=golden.query,
        skill_view_name=golden.correct_skill,
        file_path=None,
        negative=[],
        notes=golden.context or "auto-generated from golden case",
    )
