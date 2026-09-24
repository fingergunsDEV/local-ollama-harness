from __future__ import annotations

from pathlib import Path
from typing import Any

from pathspec import GitIgnoreSpec

from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword search avoids shell execution and inherits all sandbox checks."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox) -> None:
        self.settings, self.sandbox = settings, sandbox

    def _ignore_spec(self) -> GitIgnoreSpec:
        patterns = [".git/", ".harness-snapshots/", "__pycache__/", ".venv/", "node_modules/", "dist/", "build/"]
        for name in (".gitignore", ".harnessignore"):
            candidate = self.sandbox.root / name
            if candidate.is_file() and candidate.stat().st_size <= 1_000_000:
                patterns.extend(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
        return GitIgnoreSpec.from_lines(patterns)

    def keyword_search(self, query: str, path: str = ".", max_results: int = 100) -> dict[str, Any]:
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        root = self.sandbox.resolve(path, allow_root=True); results: list[dict[str, Any]] = []
        ignored = self._ignore_spec()
        for candidate in root.rglob("*"):
            if len(results) >= min(max_results, 500): break
            try:
                relative = candidate.relative_to(self.sandbox.root).as_posix()
                if ignored.match_file(relative): continue
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append({"path": self.sandbox.display(target), "line": line_number, "text": line[:500]})
                        if len(results) >= min(max_results, 500): break
            except (PermissionError, OSError, ValueError): continue
        return {"query": query, "results": results, "truncated": len(results) >= min(max_results, 500)}
