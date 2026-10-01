from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.config import Settings
from app.db.session_store import SessionStore
from app.ollama_client import OllamaClient
from app.safety.sandbox import WorkspaceSandbox


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


CREATE_EMBEDDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS file_chunk_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_path ON file_chunk_embeddings(path);
"""


class SemanticIndexer:
    """Local vector semantic search over workspace files using local Ollama embeddings."""

    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: SessionStore, client: OllamaClient) -> None:
        self.settings = settings
        self.sandbox = sandbox
        self.store = store
        self.client = client
        with self.store._lock, self.store._connect() as conn:
            conn.executescript(CREATE_EMBEDDINGS_TABLE)

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += chunk_size - overlap
        return chunks

    async def index_file(self, relative_path: str, model: str) -> int:
        target = self.sandbox.resolve(relative_path)
        if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes:
            return 0
        raw = target.read_bytes()
        if b"\x00" in raw[:8192]:
            return 0
        text = raw.decode("utf-8", errors="replace")
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        # Delete old embeddings for path
        display_path = self.sandbox.display(target)
        with self.store._lock, self.store._connect() as conn:
            conn.execute("DELETE FROM file_chunk_embeddings WHERE path=?", (display_path,))

        indexed_count = 0
        for idx, chunk in enumerate(chunks):
            try:
                vector = await self.client.embeddings(model, chunk)
                if not vector:
                    continue
                with self.store._lock, self.store._connect() as conn:
                    conn.execute(
                        "INSERT INTO file_chunk_embeddings(path, chunk_index, content, embedding_json) VALUES(?,?,?,?)",
                        (display_path, idx, chunk, json.dumps(vector)),
                    )
                indexed_count += 1
            except Exception:
                continue

        return indexed_count

    async def search(self, query: str, model: str, top_k: int = 10) -> list[dict[str, Any]]:
        query_vec = await self.client.embeddings(model, query)
        if not query_vec:
            return []

        with self.store._lock, self.store._connect() as conn:
            rows = conn.execute("SELECT path, chunk_index, content, embedding_json FROM file_chunk_embeddings").fetchall()

        results = []
        for row in rows:
            vec = json.loads(row["embedding_json"])
            score = cosine_similarity(query_vec, vec)
            results.append({
                "path": row["path"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "score": round(score, 4),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
