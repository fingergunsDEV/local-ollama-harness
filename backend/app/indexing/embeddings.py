from __future__ import annotations

import httpx
from typing import Any
from app.config import Settings
from app.safety.rate_limiter import OllamaRateLimiter


class OllamaEmbeddings:
    """Local vector embedding generator backed strictly by Ollama's local endpoints (/api/embed or /api/embeddings)."""

    def __init__(self, settings: Settings, limiter: OllamaRateLimiter, ollama_client: Any) -> None:
        self.settings = settings
        self.limiter = limiter
        self.ollama_client = ollama_client

    async def get_embedding(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Generate vector embedding for a text string using local Ollama instance."""
        if not text:
            return []

        slot = await self.limiter.generation_slot()
        async with slot:
            try:
                # Try modern Ollama /api/embed endpoint first
                response = await self.ollama_client.http.post(
                    "/api/embed",
                    json={"model": model, "input": text}
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings and isinstance(embeddings[0], list):
                        return [float(x) for x in embeddings[0]]

                # Fallback to legacy /api/embeddings endpoint
                response = await self.ollama_client.http.post(
                    "/api/embeddings",
                    json={"model": model, "prompt": text}
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding", [])
                return [float(x) for x in embedding]
            except Exception as exc:
                # Return empty list on failure or missing model
                return []
