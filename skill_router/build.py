"""Build / rebuild Chroma index from JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from skill_router.embedder import Embedder
from skill_router.schema import parse_record, record_to_chroma_metadata
from skill_router.store import delete_collection_if_exists, get_client


def load_jsonl(path: Path) -> List[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"line {line_no}: invalid JSON: {e}") from e
            records.append((line_no, raw))
    return records


def run_build(
    input_path: Path,
    chroma_dir: Path,
    *,
    reset: bool,
    model_name: str | None,
) -> int:
    rows = load_jsonl(input_path)
    if not rows:
        print("No records found in JSONL (empty or only comments).")
        return 1

    parsed = []
    for line_no, raw in rows:
        parsed.append(parse_record(raw, line_no))

    chroma_dir.mkdir(parents=True, exist_ok=True)
    if reset:
        delete_collection_if_exists(str(chroma_dir))

    embedder = Embedder(model_name=model_name)
    texts = [r.text for r in parsed]
    embeddings = embedder.encode(texts)
    ids = [r.id for r in parsed]
    metadatas = [record_to_chroma_metadata(r) for r in parsed]

    client = get_client(str(chroma_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "skill routing scenarios"},
    )
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"Indexed {len(parsed)} scenario(s) into {chroma_dir} (collection={COLLECTION_NAME}).")
    return 0
