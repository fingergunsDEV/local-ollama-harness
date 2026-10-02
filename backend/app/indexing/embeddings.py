"""Local embedding service using validated loopback Ollama instances.

Obey shared rate limits and never introduce cloud embedding providers.
"""

from __future__ import annotations

import math
from typing import Any

from app.config import Settings
from app.ollama_client import OllamaClient


class LocalEmbeddingService:
    """Provides local embedding generation and vector similarity helpers."""

    def __init__(self, settings: Settings, client: OllamaClient) -> None:
        self.settings = settings
        self.client = client

    async def generate_embeddings(self, model: str, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a list of text chunks via local Ollama."""
        if not texts:
            return []
        return await self.client.embed(model=model, input_text=texts)

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)
