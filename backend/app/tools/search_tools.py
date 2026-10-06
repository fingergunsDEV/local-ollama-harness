from __future__ import annotations

import math
from typing import Any

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword and vector similarity search inheriting sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: Any = None, embeddings_client: Any = None) -> None:
        self.settings, self.sandbox, self.store, self.embeddings_client = settings, sandbox, store, embeddings_client

    def keyword_search(self, query: str, path: str = ".", max_results: int = 100) -> dict[str, Any]:
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        root = self.sandbox.resolve(path, allow_root=True); results: list[dict[str, Any]] = []
        for candidate in root.rglob("*"):
            if len(results) >= min(max_results, 500): break
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append({"path": self.sandbox.display(target), "line": line_number, "text": line[:500]})
                        if len(results) >= min(max_results, 500): break
            except (PermissionError, OSError): continue
        return {"query": query, "results": results, "truncated": len(results) >= min(max_results, 500)}

    async def semantic_search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Perform semantic search using chunk embeddings and cosine similarity."""
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        if not self.store or not self.embeddings_client:
            return {"query": query, "results": [], "error": "Semantic search store or embeddings client unavailable"}

        query_embedding = await self.embeddings_client.get_embedding(query)
        if not query_embedding:
            # Fallback to keyword search if model is unavailable
            kw_res = self.keyword_search(query, max_results=top_k)
            return {"query": query, "results": kw_res["results"], "fallback": True}

        chunks = self.store.get_all_file_chunks()
        scored_chunks = []
        for chunk in chunks:
            emb = chunk.get("embedding_json")
            if not emb:
                # Dynamically generate missing embedding
                emb = await self.embeddings_client.get_embedding(chunk["text"])
            if emb:
                score = self._cosine_similarity(query_embedding, emb)
                scored_chunks.append({
                    "path": chunk["path"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"][:300],
                    "score": round(score, 4)
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return {"query": query, "results": scored_chunks[:top_k]}

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
