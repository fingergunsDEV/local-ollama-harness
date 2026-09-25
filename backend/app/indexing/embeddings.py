"""Local Semantic Indexing & Vector Search module.

Communicates only with local Ollama via OllamaClient over loopback.
Calculates cosine similarity in pure Python for zero external dependencies.
"""
from __future__ import annotations

import math
from typing import Any

from app.config import Settings
from app.ollama_client import OllamaClient
from app.safety.sandbox import WorkspaceSandbox


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalEmbeddingEngine:
    """Provides local vector embedding generation and semantic similarity search."""

    def __init__(self, settings: Settings, client: OllamaClient, sandbox: WorkspaceSandbox) -> None:
        self.settings = settings
        self.client = client
        self.sandbox = sandbox

    async def get_embedding(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Generate embedding vector for input text via local Ollama endpoint."""
        if not text or not text.strip():
            return []
        return await self.client.embeddings(model=model, prompt=text)

    def rank_documents(self, query_vector: list[float], documents: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        """
        Rank documents by cosine similarity to query vector.
        Each document dict should contain 'path', 'text', and 'embedding' (list[float]).
        """
        if not query_vector or not documents:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in documents:
            doc_vec = doc.get("embedding", [])
            if not doc_vec:
                continue
            sim = cosine_similarity(query_vector, doc_vec)
            scored.append((sim, {
                "path": doc.get("path", ""),
                "score": round(sim, 4),
                "text": doc.get("text", "")[:500],
            }))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
