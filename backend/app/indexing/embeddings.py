"""Semantic indexing implementation using local Ollama embeddings.

Calls only the validated Ollama /api/embeddings endpoint via OllamaClient and obeys the
shared OllamaRateLimiter. It never introduces a third-party or cloud embedding provider.
"""

from __future__ import annotations

import math
from typing import Any

from app.ollama_client import OllamaClient, OllamaUnavailable


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class LocalEmbeddings:
    """Local vector embeddings manager backed strictly by the local Ollama daemon."""
    def __init__(self, ollama_client: OllamaClient) -> None:
        self.client = ollama_client

    async def get_embedding(self, model: str, text: str) -> list[float]:
        if not text.strip():
            return []
        return await self.client.embed(model, text)

    def search_vectors(
        self, query_vector: list[float], doc_vectors: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results = []
        for doc in doc_vectors:
            score = cosine_similarity(query_vector, doc.get("vector", []))
            results.append({**doc, "score": score})
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]
