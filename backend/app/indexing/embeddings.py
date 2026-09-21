from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

from app.config import Settings
from app.db.session_store import SessionStore
from app.indexing.indexer import LocalIndexer
from app.ollama_client import OllamaClient, OllamaUnavailable
from app.safety.sandbox import WorkspaceSandbox


class LocalEmbeddings:
    """Local semantic search engine using Ollama local embeddings and SQLite vector store."""

    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: SessionStore, client: OllamaClient) -> None:
        self.settings, self.sandbox, self.store, self.client = settings, sandbox, store, client
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.store._lock, self.store._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS file_embeddings (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                model TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            )
            """)

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def index_file(self, path_str: str, model: str = "nomic-embed-text") -> bool:
        try:
            path = self.sandbox.resolve(path_str)
            if not path.is_file() or path.stat().st_size > self.settings.max_file_read_bytes:
                return False
            raw = path.read_bytes()
            if b"\x00" in raw[:8192]:
                return False
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                return False

            # Truncate text if too long for embedding
            embedding = await self.client.embeddings(model=model, prompt=text[:8000])
            if not embedding:
                return False

            display_path = self.sandbox.display(path)
            vector_json = json.dumps(embedding)
            now_iso = datetime.now(UTC).isoformat()

            with self.store._lock, self.store._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO file_embeddings VALUES (?, ?, ?, ?, ?)",
                    (display_path, "", model, vector_json, now_iso)
                )
            return True
        except (OSError, PermissionError, ValueError, OllamaUnavailable):
            return False

    async def search(self, query: str, model: str = "nomic-embed-text", top_k: int = 5) -> dict[str, Any]:
        if not query or len(query) > 500:
            raise ValueError("query must be 1-500 characters")

        query_vector = await self.client.embeddings(model=model, prompt=query)
        if not query_vector:
            return {"query": query, "results": [], "count": 0}

        with self.store._lock, self.store._connect() as conn:
            rows = conn.execute("SELECT path, vector_json FROM file_embeddings WHERE model=?", (model,)).fetchall()

        scored: list[tuple[float, str]] = []
        for row in rows:
            path_display = row["path"]
            doc_vector = json.loads(row["vector_json"])
            score = self._cosine_similarity(query_vector, doc_vector)
            scored.append((score, path_display))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {"path": path, "score": round(score, 4)}
            for score, path in scored[:top_k]
        ]
        return {"query": query, "results": results, "count": len(results)}
