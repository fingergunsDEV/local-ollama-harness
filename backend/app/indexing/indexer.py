from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pathspec import GitIgnoreSpec

from app.config import Settings
from app.db.session_store import SessionStore
from app.safety.sandbox import WorkspaceSandbox


class LocalIndexer:
    """Capped metadata and chunk indexer that honors .gitignore and harnessignore."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: SessionStore, embeddings_client: Any = None) -> None:
        self.settings, self.sandbox, self.store = settings, sandbox, store
        self.embeddings_client = embeddings_client

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
                    display_path = self.sandbox.display(path)

                    # Check if file changed
                    existing = conn.execute("SELECT hash FROM file_index WHERE path=?", (display_path,)).fetchone()
                    if not existing or existing["hash"] != digest:
                        conn.execute("INSERT OR REPLACE INTO file_index VALUES(?,?,?,?,?)", (display_path, digest, stat.st_size, stat.st_mtime, datetime.now(UTC).isoformat()))
                        # Re-chunk text files
                        conn.execute("DELETE FROM file_chunks WHERE path=?", (display_path,))
                        content_str = raw.decode("utf-8", errors="replace")
                        chunks = self._chunk_text(content_str)
                        for idx, chunk in enumerate(chunks):
                            conn.execute(
                                "INSERT INTO file_chunks(id, path, chunk_index, text, embedding_json) VALUES(?,?,?,?,?)",
                                (str(uuid.uuid4()), display_path, idx, chunk, None)
                            )
                    indexed += 1
                except (OSError, PermissionError): continue
        return {"indexed": indexed, "truncated": len(candidates) > self.settings.max_files_indexed}

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks
