from __future__ import annotations

import math
from typing import Any

from app.ollama_client import OllamaClient


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class LocalSemanticIndexer:
    """Local semantic search engine utilizing validated loopback Ollama embeddings."""

    def __init__(self, ollama: OllamaClient, model: str = "nomic-embed-text") -> None:
        self.ollama = ollama
        self.model = model

    async def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            return []
        return await self.ollama.embeddings(self.model, text)

    async def rank_documents(self, query: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_vec = await self.embed_text(query)
        if not query_vec:
            return documents
        results = []
        for doc in documents:
            content = str(doc.get("content") or doc.get("text") or "")
            if not content:
                results.append({**doc, "score": 0.0})
                continue
            doc_vec = await self.embed_text(content[:1000])
            score = cosine_similarity(query_vec, doc_vec)
            results.append({**doc, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
