from __future__ import annotations

from typing import Any

from app.config import Settings
from app.db.session_store import SessionStore
from app.ollama_client import OllamaClient
from app.safety.sandbox import WorkspaceSandbox


class OllamaEmbedder:
    """Generates local embeddings via Ollama and indexes workspace content into SQLite."""

    def __init__(self, settings: Settings, client: OllamaClient, store: SessionStore, sandbox: WorkspaceSandbox) -> None:
        self.settings, self.client, self.store, self.sandbox = settings, client, store, sandbox

    async def embed_text(self, model: str, text: str) -> list[float]:
        embeddings = await self.client.embed(model, text)
        return embeddings[0] if embeddings else []

    async def index_file(self, model: str, relative_path: str, chunk_size: int = 500) -> dict[str, Any]:
        target = self.sandbox.resolve(relative_path)
        self.sandbox.ensure_regular_file(target)
        raw_text = target.read_text(encoding="utf-8", errors="replace")

        chunks = [raw_text[i:i + chunk_size] for i in range(0, len(raw_text), chunk_size) if raw_text[i:i + chunk_size].strip()]
        stored_ids = []
        for index, chunk in enumerate(chunks):
            embedding = await self.embed_text(model, chunk)
            if embedding:
                embedding_id = self.store.store_embedding(self.sandbox.display(target), index, chunk, embedding)
                stored_ids.append(embedding_id)

        return {"path": self.sandbox.display(target), "chunks_indexed": len(stored_ids)}
