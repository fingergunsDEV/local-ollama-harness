"""Local semantic indexing using Ollama embeddings."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ollama_client import OllamaClient


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalEmbeddings:
    """Handles local embedding generation via OllamaClient."""
    def __init__(self, client: OllamaClient, default_model: str = "nomic-embed-text") -> None:
        self.client = client
        self.default_model = default_model

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        target_model = model or self.default_model
        return await self.client.embeddings(target_model, text)
