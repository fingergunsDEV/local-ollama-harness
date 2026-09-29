from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword and regex search avoids shell execution and inherits all sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox) -> None:
        self.settings, self.sandbox = settings, sandbox

    def keyword_search(
        self,
        query: str,
        path: str = ".",
        max_results: int = 100,
        is_regex: bool = False,
        file_pattern: str | None = None,
    ) -> dict[str, Any]:
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        root = self.sandbox.resolve(path, allow_root=True); results: list[dict[str, Any]] = []

        pattern = None
        if is_regex:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"invalid regex pattern: {exc}") from exc

        ext_filter = file_pattern.lower() if file_pattern else None

        for candidate in root.rglob("*"):
            if len(results) >= min(max_results, 500): break
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                if ext_filter and not target.name.lower().endswith(ext_filter) and not candidate.match(file_pattern or ""):
                    continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    matched = pattern.search(line) if pattern else (query.lower() in line.lower())
                    if matched:
                        results.append({"path": self.sandbox.display(target), "line": line_number, "text": line[:500]})
                        if len(results) >= min(max_results, 500): break
            except (PermissionError, OSError): continue
        return {"query": query, "results": results, "truncated": len(results) >= min(max_results, 500), "is_regex": is_regex}
