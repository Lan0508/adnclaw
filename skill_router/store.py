"""Chroma persistent store."""

from __future__ import annotations

import chromadb

COLLECTION_NAME = "skill_scenarios"


def get_client(chroma_dir: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=chroma_dir)


def get_collection(chroma_dir: str):
    client = get_client(chroma_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "skill routing scenarios"},
    )


def delete_collection_if_exists(chroma_dir: str) -> None:
    client = get_client(chroma_dir)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
