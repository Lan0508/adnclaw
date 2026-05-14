"""Query index and return routing hints with threshold and hybrid search."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from skill_router.retrieval.bm25 import BM25Index, get_bm25_path
from skill_router.core.embedder import Embedder
from skill_router.core.hints import format_routing_hints
from skill_router.core.schema import metadata_to_hit
from skill_router.core.store import DEFAULT_DISTANCE_THRESHOLD, get_collection

TOP_K = 3


def _merge_rrf(
    vector_hits: List[Tuple[str, float]],
    bm25_hits: List[Tuple[str, float]],
    k: int = 60,
) -> List[str]:
    scores = {}
    for rank, (doc_id, _) in enumerate(vector_hits, 1):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    for rank, (doc_id, _) in enumerate(bm25_hits, 1):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in ranked]


def run_query(
    question: str,
    chroma_dir: Path,
    *,
    model_name: str | None,
    threshold: float | None = None,
    hybrid: bool = False,
) -> str:
    question = (question or "").strip()
    if not question:
        return format_routing_hints([])

    collection = get_collection(str(chroma_dir))
    count = collection.count()
    if count == 0:
        return format_routing_hints([])

    threshold = threshold if threshold is not None else DEFAULT_DISTANCE_THRESHOLD
    embedder = Embedder(model_name=model_name)
    q_emb = embedder.encode([question])[0]
    n = min(TOP_K * 2, count) if hybrid else min(TOP_K, count)
    result = collection.query(
        query_embeddings=[q_emb],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )

    ids_list = result.get("ids") or [[]]
    docs_list = result.get("documents") or [[]]
    meta_list = result.get("metadatas") or [[]]
    dist_list = result.get("distances") or [[]]

    ids0 = ids_list[0] if ids_list else []
    docs0 = docs_list[0] if docs_list else []
    meta0 = meta_list[0] if meta_list else []
    dist0 = dist_list[0] if dist_list else []

    vector_hits: List[Tuple[str, float]] = []
    for i, _id in enumerate(ids0):
        dist = dist0[i] if i < len(dist0) else float("inf")
        if dist <= threshold:
            vector_hits.append((_id, dist))

    ordered_ids: List[str] = [h[0] for h in vector_hits[:TOP_K]]

    if hybrid:
        bm25_path = get_bm25_path(chroma_dir)
        bm25_index = BM25Index.load(bm25_path)
        bm25_hits = bm25_index.query(question, top_k=TOP_K * 2)
        bm25_hits = [(doc_id, score) for doc_id, score in bm25_hits if score > 0]
        ordered_ids = _merge_rrf(vector_hits, bm25_hits)[:TOP_K]

    id_set = set(ordered_ids)
    meta_map = {}
    doc_map = {}
    for i, _id in enumerate(ids0):
        if _id in id_set:
            doc_map[_id] = docs0[i] if i < len(docs0) else ""
            meta = meta0[i] if i < len(meta0) else {}
            if not isinstance(meta, dict):
                meta = {}
            meta_map[_id] = meta

    hits: List[dict] = []
    for _id in ordered_ids:
        doc = doc_map.get(_id, "")
        meta = meta_map.get(_id, {})
        hits.append(metadata_to_hit(str(doc or ""), meta))

    return format_routing_hints(hits)
