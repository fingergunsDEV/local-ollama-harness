from __future__ import annotations

from typing import Any

from app.ollama_client import OllamaClient


class LocalEmbeddings:
    """Local text embedding generator backed solely by the validated Ollama loopback client."""

    def __init__(self, client: OllamaClient, default_model: str = "nomic-embed-text") -> None:
        self.client = client
        self.default_model = default_model

    async def embed_query(self, text: str, model: str | None = None) -> list[float]:
        """Generate a vector embedding for a single query text."""
        model_name = model or self.default_model
        embeddings = await self.client.embed(model=model_name, input_text=text)
        if not embeddings:
            return []
        return embeddings[0]

    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate vector embeddings for a list of document texts."""
        if not texts:
            return []
        model_name = model or self.default_model
        return await self.client.embed(model=model_name, input_text=texts)
