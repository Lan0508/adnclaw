"""BM25 indexer for hybrid retrieval."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


def tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"\w+", text)
    return tokens


class BM25Index:
    def __init__(self) -> None:
        self._doc_ids: List[str] = []
        self._texts: List[str] = []
        self._bm25 = None

    def add(self, doc_id: str, text: str) -> None:
        self._doc_ids.append(doc_id)
        self._texts.append(text)

    def build(self) -> None:
        if not self._texts:
            return
        from rank_bm25 import BM25Okapi

        tokenized = [tokenize(t) for t in self._texts]
        self._bm25 = BM25Okapi(tokenized)

    def query(self, q: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._bm25 is None or not self._doc_ids:
            return []
        tokens = tokenize(q)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self._doc_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]

    def save(self, path: Path) -> None:
        data = {
            "doc_ids": self._doc_ids,
            "texts": self._texts,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        idx = cls()
        if not path.exists():
            return idx
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        idx._doc_ids = data.get("doc_ids", [])
        idx._texts = data.get("texts", [])
        idx.build()
        return idx


BM25_INDEX_FILE = "bm25_index.json"


def get_bm25_path(chroma_dir: Path) -> Path:
    return chroma_dir / BM25_INDEX_FILE