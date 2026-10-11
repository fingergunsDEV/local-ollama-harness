from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.indexing.embeddings import LocalEmbeddingProvider
from app.indexing.indexer import LocalIndexer
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python search tools inheriting sandbox checks and local embeddings capability."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, indexer: LocalIndexer | None = None) -> None:
        self.settings, self.sandbox, self.indexer = settings, sandbox, indexer

    def keyword_search(self, query: str, path: str = ".", max_results: int = 100) -> dict[str, Any]:
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        root = self.sandbox.resolve(path, allow_root=True); results: list[dict[str, Any]] = []
        for candidate in root.rglob("*"):
            if len(results) >= min(max_results, 500): break
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append({"path": self.sandbox.display(target), "line": line_number, "text": line[:500]})
                        if len(results) >= min(max_results, 500): break
            except (PermissionError, OSError): continue
        return {"query": query, "results": results, "truncated": len(results) >= min(max_results, 500)}

    async def semantic_search(self, query: str, provider: LocalEmbeddingProvider, top_k: int = 5) -> dict[str, Any]:
        """Perform semantic code search using local embeddings."""
        if not query or len(query) > 500:
            raise ValueError("query must be 1-500 characters")
        if not self.indexer:
            return {"query": query, "results": [], "error": "Indexer not initialized"}

        try:
            query_vectors = await provider.embed(query)
            if not query_vectors:
                return {"query": query, "results": []}
            results = self.indexer.search_embeddings(query_vectors[0], top_k=top_k)
            return {"query": query, "results": results}
        except Exception as exc:
            return {"query": query, "results": [], "error": str(exc)}
