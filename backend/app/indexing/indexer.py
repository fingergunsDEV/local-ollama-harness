from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pathspec import GitIgnoreSpec

from app.config import Settings
from app.db.session_store import SessionStore
from app.indexing.embeddings import LocalEmbeddingProvider, chunk_text, cosine_similarity
from app.safety.sandbox import WorkspaceSandbox


class LocalIndexer:
    """Capped metadata and vector index that honors .gitignore and the harness-specific ignore file."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, store: SessionStore) -> None:
        self.settings, self.sandbox, self.store = settings, sandbox, store
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure file_embeddings table exists in SQLite store."""
        schema = """
        CREATE TABLE IF NOT EXISTS file_embeddings (
          id TEXT PRIMARY KEY,
          path TEXT NOT NULL,
          chunk_index INTEGER NOT NULL,
          chunk_text TEXT NOT NULL,
          embedding_json TEXT NOT NULL,
          indexed_at TEXT NOT NULL,
          FOREIGN KEY(path) REFERENCES file_index(path) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_embeddings_path ON file_embeddings(path);
        """
        with self.store._lock, self.store._connect() as conn:
            conn.executescript(schema)

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

    async def generate_embeddings_for_file(self, display_path: str, provider: LocalEmbeddingProvider) -> int:
        """Chunk a file and compute vector embeddings via local Ollama."""
        try:
            full_path = self.sandbox.resolve(self.sandbox.root / display_path)
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return 0

        chunks = chunk_text(content, chunk_size=500, overlap=50)
        if not chunks:
            return 0

        try:
            vectors = await provider.embed(chunks)
        except Exception:
            return 0

        now_iso = datetime.now(UTC).isoformat()
        with self.store._lock, self.store._connect() as conn:
            conn.execute("DELETE FROM file_embeddings WHERE path=?", (display_path,))
            for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
                chunk_id = f"{display_path}#{idx}"
                conn.execute(
                    "INSERT OR REPLACE INTO file_embeddings VALUES(?,?,?,?,?,?)",
                    (chunk_id, display_path, idx, chunk, json.dumps(vec), now_iso),
                )
        return len(chunks)

    def search_embeddings(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Perform vector cosine similarity search over stored chunk embeddings."""
        with self.store._lock, self.store._connect() as conn:
            rows = conn.execute("SELECT path, chunk_index, chunk_text, embedding_json FROM file_embeddings").fetchall()

        results: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            vec = json.loads(row["embedding_json"])
            sim = cosine_similarity(query_vector, vec)
            results.append((sim, {
                "path": row["path"],
                "chunk_index": row["chunk_index"],
                "chunk_text": row["chunk_text"],
                "score": round(sim, 4),
            }))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]
