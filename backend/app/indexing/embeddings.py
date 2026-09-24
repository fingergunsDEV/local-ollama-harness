from __future__ import annotations

import math
from typing import Any

from app.ollama_client import OllamaClient


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2): return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)


class LocalEmbeddings:
    """Local embedding manager using the validated Ollama client only."""
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def generate_embedding(self, model: str, text: str) -> list[float]:
        embeddings = await self.client.embed(model, text)
        return embeddings[0] if embeddings else []

    @staticmethod
    def rank_texts(query_vector: list[float], text_vectors: list[tuple[str, list[float]]], top_k: int = 5) -> list[dict[str, Any]]:
        scored = []
        for text, vec in text_vectors:
            score = cosine_similarity(query_vector, vec)
            scored.append({"text": text, "score": score})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]
