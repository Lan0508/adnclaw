"""sentence-transformers wrapper (lazy load)."""

from __future__ import annotations

import os
from typing import List

import numpy as np


os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.environ.get(
            "SKILL_ROUTER_MODEL", DEFAULT_MODEL
        )
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        if not texts:
            return []
        arr = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 32,
            convert_to_numpy=True,
        )
        if isinstance(arr, np.ndarray):
            return arr.tolist()
        return [np.asarray(row, dtype=np.float32).tolist() for row in arr]
