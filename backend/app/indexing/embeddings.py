from __future__ import annotations

import math
from typing import Any

from app.ollama_client import OllamaClient, OllamaUnavailable


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot_product / (norm1 * norm2)


class OllamaEmbeddings:
    """Local vector embeddings generated purely via Ollama /api/embed."""

    def __init__(self, client: OllamaClient, default_model: str = "nomic-embed-text") -> None:
        self.client = client
        self.default_model = default_model

    async def get_embeddings(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        target_model = model or self.default_model
        try:
            return await self.client.embed(target_model, texts)
        except OllamaUnavailable:
            return []

    async def get_embedding(self, text: str, model: str | None = None) -> list[float]:
        results = await self.get_embeddings([text], model=model)
        return results[0] if results else []
