"""Local semantic embeddings via Ollama /api/embed or /api/embeddings.

Ollama's /api/embed endpoint returns float vectors for given text snippets.
All calls must be local-only and obey the Ollama rate limiter.
"""
from __future__ import annotations

import math
from typing import Any

import httpx

from app.config import Settings
from app.safety.rate_limiter import OllamaRateLimiter


class LocalEmbeddings:
    """Computes vector embeddings via local Ollama and calculates vector similarity."""

    def __init__(self, settings: Settings, limiter: OllamaRateLimiter | None = None) -> None:
        self.settings = settings
        self.limiter = limiter
        self.http = httpx.AsyncClient(
            base_url=settings.ollama_host.rstrip("/"),
            timeout=httpx.Timeout(90, connect=5),
            trust_env=False,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Fetch embedding vector for text using local Ollama endpoint."""
        if not text or not text.strip():
            return []
        payload = {"model": model, "input": text}
        if self.limiter:
            slot = await self.limiter.generation_slot()
            async with slot:
                res = await self.http.post("/api/embed", json=payload)
        else:
            res = await self.http.post("/api/embed", json=payload)

        if res.status_code == 404:
            # Fallback to legacy /api/embeddings endpoint if /api/embed is not available
            payload_legacy = {"model": model, "prompt": text}
            if self.limiter:
                slot = await self.limiter.generation_slot()
                async with slot:
                    res = await self.http.post("/api/embeddings", json=payload_legacy)
            else:
                res = await self.http.post("/api/embeddings", json=payload_legacy)
            res.raise_for_status()
            data = res.json()
            return data.get("embedding", [])

        res.raise_for_status()
        data = res.json()
        embeddings = data.get("embeddings", [])
        if embeddings and isinstance(embeddings[0], list):
            return embeddings[0]
        return data.get("embedding", [])

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
