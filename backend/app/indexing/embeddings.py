from __future__ import annotations

import math
from typing import Any

from app.ollama_client import OllamaClient


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class LocalEmbeddingService:
    """Local vector embedding generator and similarity matching powered by Ollama."""

    def __init__(self, ollama_client: OllamaClient, default_model: str = "nomic-embed-text") -> None:
        self.client = ollama_client
        self.model = default_model

    async def get_embedding(self, text: str) -> list[float]:
        """Fetch embedding vector for a given text snippet."""
        if not text.strip():
            return []
        return await self.client.embeddings(self.model, text)

    async def rank_by_similarity(self, query: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank documents by vector cosine similarity against query."""
        query_vec = await self.get_embedding(query)
        if not query_vec:
            return documents

        results = []
        for doc in documents:
            text = doc.get("content") or doc.get("text") or ""
            doc_vec = await self.get_embedding(text)
            sim = cosine_similarity(query_vec, doc_vec) if doc_vec else 0.0
            doc_copy = dict(doc)
            doc_copy["similarity"] = sim
            results.append(doc_copy)

        results.sort(key=lambda item: item.get("similarity", 0.0), reverse=True)
        return results
