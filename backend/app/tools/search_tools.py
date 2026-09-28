from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python search tools avoid shell execution and inherit all sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, embedding_manager: Any = None) -> None:
        self.settings, self.sandbox, self.embedding_manager = settings, sandbox, embedding_manager

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

    def regex_search(self, pattern: str, path: str = ".", file_pattern: str = "*", max_results: int = 100) -> dict[str, Any]:
        """Search files using regular expressions and optional file glob matching."""
        if not pattern or len(pattern) > 500:
            raise ValueError("pattern must be 1-500 characters")
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f"invalid regex pattern: {exc}") from exc

        root = self.sandbox.resolve(path, allow_root=True)
        results: list[dict[str, Any]] = []

        for candidate in root.rglob(file_pattern):
            if len(results) >= min(max_results, 500):
                break
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes:
                    continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]:
                    continue
                for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        results.append({"path": self.sandbox.display(target), "line": line_number, "text": line[:500]})
                        if len(results) >= min(max_results, 500):
                            break
            except (PermissionError, OSError):
                continue

        return {"pattern": pattern, "file_pattern": file_pattern, "results": results, "truncated": len(results) >= min(max_results, 500)}

    async def semantic_search(self, query: str, model: str = "nomic-embed-text", limit: int = 10) -> dict[str, Any]:
        """Perform semantic vector similarity search over indexed code embeddings."""
        if not self.embedding_manager:
            return {"query": query, "results": [], "error": "Embedding manager not configured"}
        try:
            results = await self.embedding_manager.search(query, model=model, limit=limit)
            return {"query": query, "results": results}
        except Exception as exc:
            return {"query": query, "results": [], "error": str(exc)}
