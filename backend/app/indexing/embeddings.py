from __future__ import annotations

import math
from typing import Any

from app.config import Settings
from app.ollama_client import OllamaClient


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class OllamaEmbeddings:
    """Computes vector embeddings using the local, loopback-validated Ollama /api/embed endpoint.

    Strictly enforces local-only execution and uses the shared OllamaRateLimiter.
    """
    def __init__(self, settings: Settings, client: OllamaClient) -> None:
        self.settings = settings
        self.client = client

    async def get_embeddings(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self.client.embed(model, texts)

    async def search_similar(self, model: str, query: str, documents: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        """Given a query and candidate document dicts with 'content' or 'text', returns top_k similar documents."""
        if not documents or not query:
            return []
        texts = [doc.get("content") or doc.get("text") or "" for doc in documents]
        all_embeddings = await self.get_embeddings(model, [query] + texts)
        if not all_embeddings or len(all_embeddings) < len(texts) + 1:
            return []
        query_vec = all_embeddings[0]
        doc_vecs = all_embeddings[1:]
        scored = []
        for doc, vec in zip(documents, doc_vecs):
            sim = cosine_similarity(query_vec, vec)
            item = dict(doc)
            item["similarity"] = sim
            scored.append(item)
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]
