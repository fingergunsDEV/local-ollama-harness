from __future__ import annotations

import json
import math
from typing import Any

from app.config import Settings
from app.db.session_store import SessionStore
from app.ollama_client import OllamaClient, OllamaUnavailable


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vector lists."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class EmbeddingManager:
    """Handles local vector embedding generation and cosine similarity search over code chunks."""

    def __init__(self, settings: Settings, store: SessionStore, client: OllamaClient) -> None:
        self.settings, self.store, self.client = settings, store, client
        self._ensure_table()

    def _ensure_table(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS file_embeddings (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_embeddings_path ON file_embeddings(path);
        """
        with self.store._lock, self.store._connect() as conn:
            conn.executescript(schema)

    async def store_chunk_embedding(self, path: str, chunk_index: int, chunk_text: str, model: str) -> None:
        embeddings = await self.client.embed(model, chunk_text)
        if not embeddings:
            return
        vec = embeddings[0]
        chunk_id = f"{path}:{chunk_index}"
        record = (chunk_id, path, chunk_index, chunk_text, json.dumps(vec), model, self.store.now() if hasattr(self.store, 'now') else "now")
        with self.store._lock, self.store._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO file_embeddings VALUES(?,?,?,?,?,?,datetime('now'))",
                (chunk_id, path, chunk_index, chunk_text, json.dumps(vec), model)
            )

    async def search(self, query: str, model: str, limit: int = 10) -> list[dict[str, Any]]:
        query_vecs = await self.client.embed(model, query)
        if not query_vecs:
            return []
        q_vec = query_vecs[0]

        with self.store._lock, self.store._connect() as conn:
            rows = conn.execute("SELECT path, chunk_index, chunk_text, embedding_json FROM file_embeddings WHERE model=?", (model,)).fetchall()

        results = []
        for row in rows:
            vec = json.loads(row["embedding_json"])
            score = cosine_similarity(q_vec, vec)
            results.append({
                "path": row["path"],
                "chunk_index": row["chunk_index"],
                "text": row["chunk_text"],
                "score": score
            })

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]
