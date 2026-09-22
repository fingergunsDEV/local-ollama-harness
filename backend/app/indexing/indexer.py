from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pathspec import GitIgnoreSpec

from app.config import Settings
from app.db.session_store import SessionStore
from app.safety.sandbox import WorkspaceSandbox


class LocalIndexer:
    """Capped metadata index that honors .gitignore and the harness-specific ignore file."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: SessionStore) -> None:
        self.settings, self.sandbox, self.store = settings, sandbox, store

    def _ignore_spec(self) -> GitIgnoreSpec:
        patterns = [".git/", ".harness-snapshots/", "__pycache__/", ".venv/", "node_modules/", "dist/", "build/"]
        for name in (".gitignore", ".harnessignore"):
            candidate = self.sandbox.root / name
            if candidate.is_file() and candidate.stat().st_size <= 1_000_000:
                patterns.extend(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
        return GitIgnoreSpec.from_lines(patterns)

    def refresh(self) -> dict[str, int | bool]:
        ignored = self._ignore_spec()
        candidates: list[Path] = []
        for candidate in self.sandbox.root.rglob("*"):
            if not candidate.is_file(): continue
            relative = candidate.relative_to(self.sandbox.root).as_posix()
            if ignored.match_file(relative): continue
            candidates.append(candidate)
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        indexed = 0
        with self.store._lock, self.store._connect() as conn:
            for candidate in candidates[:self.settings.max_files_indexed]:
                try:
                    path = self.sandbox.resolve(candidate); raw = path.read_bytes()
                    if b"\x00" in raw[:8192]: continue
                    stat = path.stat(); digest = hashlib.sha256(raw).hexdigest()
                    conn.execute("INSERT OR REPLACE INTO file_index VALUES(?,?,?,?,?)", (self.sandbox.display(path), digest, stat.st_size, stat.st_mtime, datetime.now(UTC).isoformat()))
                    indexed += 1
                except (OSError, PermissionError): continue
        return {"indexed": indexed, "truncated": len(candidates) > self.settings.max_files_indexed}
