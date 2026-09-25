from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword search avoids shell execution and inherits all sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox) -> None:
        self.settings, self.sandbox = settings, sandbox

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

    def semantic_search(self, query: str, path: str = ".", top_k: int = 5) -> dict[str, Any]:
        """Local semantic / fuzzy code search over workspace text files."""
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        root = self.sandbox.resolve(path, allow_root=True); candidates: list[dict[str, Any]] = []
        query_words = set(query.lower().split())
        for candidate in root.rglob("*"):
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                content = raw.decode("utf-8", errors="replace")
                matched_lines = []
                total_matches = 0
                for idx, line in enumerate(content.splitlines(), 1):
                    line_words = set(line.lower().split())
                    common = query_words.intersection(line_words)
                    if common:
                        total_matches += len(common)
                        if len(matched_lines) < 3:
                            matched_lines.append({"line": idx, "text": line[:300]})
                if total_matches > 0:
                    candidates.append({"path": self.sandbox.display(target), "relevance": total_matches, "matches": matched_lines})
            except (PermissionError, OSError): continue
        candidates.sort(key=lambda x: x["relevance"], reverse=True)
        return {"query": query, "results": candidates[:top_k]}
