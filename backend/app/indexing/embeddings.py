from __future__ import annotations

from typing import Any

import httpx

from app.ollama_client import OllamaClient, OllamaUnavailable


class OllamaEmbeddings:
    """Local vector embeddings generated via Ollama's /api/embed or /api/embeddings endpoints.

    Always uses the validated loopback OllamaClient and respects rate limits.
    """

    def __init__(self, client: OllamaClient, default_model: str = "nomic-embed-text") -> None:
        self.client = client
        self.default_model = default_model

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """Generate vector embedding for a single text string."""
        results = await self.embed_batch([text], model=model)
        if not results:
            return []
        return results[0]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate vector embeddings for a batch of text strings.

        Tries the newer /api/embed endpoint first, falling back to /api/embeddings.
        """
        if not texts:
            return []

        target_model = model or self.default_model
        slot = await self.client.limiter.generation_slot()

        async with slot:
            try:
                # Try Ollama /api/embed (introduced in recent Ollama versions, supports batching)
                response = await self.client.http.post(
                    "/api/embed",
                    json={"model": target_model, "input": texts},
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if isinstance(embeddings, list):
                        return embeddings

                # Fallback to single /api/embeddings requests if /api/embed is unavailable
                embeddings_list: list[list[float]] = []
                for text in texts:
                    res = await self.client.http.post(
                        "/api/embeddings",
                        json={"model": target_model, "prompt": text},
                    )
                    res.raise_for_status()
                    data = res.json()
                    embedding = data.get("embedding", [])
                    embeddings_list.append(embedding)

                return embeddings_list
            except httpx.HTTPError as exc:
                raise OllamaUnavailable("Ollama embedding generation failed") from exc
