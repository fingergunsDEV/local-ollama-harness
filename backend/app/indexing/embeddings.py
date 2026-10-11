from __future__ import annotations

import json
import math
from typing import Any

import httpx

from app.config import Settings
from app.safety.rate_limiter import OllamaRateLimiter


class EmbeddingError(RuntimeError):
    """Raised when local embedding generation fails."""


class LocalEmbeddingProvider:
    """Local vector embeddings using Ollama's /api/embed or /api/embeddings endpoint."""

    def __init__(self, settings: Settings, limiter: OllamaRateLimiter, embedding_model: str = "nomic-embed-text") -> None:
        self.settings = settings
        self.limiter = limiter
        self.model = embedding_model or "nomic-embed-text"
        self.http = httpx.AsyncClient(
            base_url=settings.ollama_host.rstrip("/"),
            timeout=httpx.Timeout(30, connect=5),
            trust_env=False,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings for text or a batch of texts using local Ollama."""
        slot = await self.limiter.generation_slot()
        async with slot:
            try:
                payload = {"model": self.model, "input": text}
                response = await self.http.post("/api/embed", json=payload)
                if response.status_code == 404:
                    # Fallback for older Ollama versions using /api/embeddings
                    if isinstance(text, list):
                        embeddings = []
                        for item in text:
                            res = await self.http.post("/api/embeddings", json={"model": self.model, "prompt": item})
                            res.raise_for_status()
                            embeddings.append(res.json()["embedding"])
                        return embeddings
                    else:
                        res = await self.http.post("/api/embeddings", json={"model": self.model, "prompt": text})
                        res.raise_for_status()
                        return [res.json()["embedding"]]

                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                if not embeddings and "embedding" in data:
                    embeddings = [data["embedding"]]
                return embeddings
            except httpx.HTTPError as exc:
                raise EmbeddingError(f"Embedding request failed: {exc}") from exc


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vector lists."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character chunks."""
    if not text.strip():
        return []
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > chunk_size and current_chunk:
            chunks.append("".join(current_chunk))
            # Overlap: keep recent lines up to overlap length
            overlap_lines: list[str] = []
            overlap_len = 0
            for prev_line in reversed(current_chunk):
                if overlap_len + len(prev_line) <= overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_len += len(prev_line)
                else:
                    break
            current_chunk = overlap_lines
            current_len = overlap_len

        current_chunk.append(line)
        current_len += len(line)

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks
