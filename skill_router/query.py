"""Query index and return routing hints (Top-K only, K=3)."""

from __future__ import annotations

from pathlib import Path
from typing import List

from skill_router.embedder import Embedder
from skill_router.hints import format_routing_hints
from skill_router.schema import metadata_to_hit
from skill_router.store import get_collection

TOP_K = 3


def run_query(
    question: str,
    chroma_dir: Path,
    *,
    model_name: str | None,
) -> str:
    question = (question or "").strip()
    if not question:
        return format_routing_hints([])

    collection = get_collection(str(chroma_dir))
    count = collection.count()
    if count == 0:
        return format_routing_hints([])

    embedder = Embedder(model_name=model_name)
    q_emb = embedder.encode([question])[0]
    n = min(TOP_K, count)
    result = collection.query(
        query_embeddings=[q_emb],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )

    ids_list = result.get("ids") or [[]]
    docs_list = result.get("documents") or [[]]
    meta_list = result.get("metadatas") or [[]]

    hits: List[dict] = []
    ids0 = ids_list[0] if ids_list else []
    docs0 = docs_list[0] if docs_list else []
    meta0 = meta_list[0] if meta_list else []

    for i, _id in enumerate(ids0):
        doc = docs0[i] if i < len(docs0) else ""
        meta = meta0[i] if i < len(meta0) else {}
        if not isinstance(meta, dict):
            meta = {}
        hits.append(metadata_to_hit(str(doc or ""), meta))

    return format_routing_hints(hits)
