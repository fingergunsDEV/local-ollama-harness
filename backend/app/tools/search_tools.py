from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword search avoids shell execution and inherits all sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, embeddings: Any = None) -> None:
        self.settings, self.sandbox, self.embeddings = settings, sandbox, embeddings

    async def semantic_search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        if not self.embeddings:
            return {"query": query, "results": [], "error": "embeddings engine disabled or unavailable"}
        return await self.embeddings.search(query=query, top_k=top_k)

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
