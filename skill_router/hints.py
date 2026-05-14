"""Format [Skill routing hints] block for Hermes."""

from __future__ import annotations

from typing import Any, List

HEADER = (
    "[Skill routing hints — scenario retrieval; prefer these when relevant]"
)


def _truncate(s: str, max_len: int = 280) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def format_routing_hints(hits: List[dict[str, Any]]) -> str:
    if not hits:
        return (
            f"{HEADER}\n"
            "(No indexed scenarios matched the query, or the index is empty. "
            "Run `build` first.)"
        )

    lines = [HEADER]
    for h in hits:
        text = _truncate(str(h.get("text", "")))
        svn = str(h.get("skill_view_name", "")).strip()
        lines.append(f"- Match: {text}")
        lines.append(f"  → skill_view(name='{svn}')")
        fp = h.get("file_path")
        if fp:
            lines.append(
                f"  → skill_view(name='{svn}', file_path='{str(fp).strip()}')"
            )
        neg = h.get("negative") or []
        if neg:
            joined = ", ".join(str(x) for x in neg)
            lines.append(f"  → Do not use for this: {joined}")
        notes = str(h.get("notes", "") or "").strip()
        if notes:
            lines.append(f"  Note: {notes}")
    return "\n".join(lines)
