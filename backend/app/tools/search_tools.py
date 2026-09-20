from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.indexing.embeddings import OllamaEmbeddings, cosine_similarity
from app.safety.sandbox import WorkspaceSandbox


class SearchTools:
    """Pure-Python keyword and semantic vector search within workspace sandbox bounds."""
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

    async def semantic_search(
        self,
        query: str,
        embeddings: OllamaEmbeddings | None = None,
        path: str = ".",
        max_results: int = 10,
        embedding_model: str | None = None
    ) -> dict[str, Any]:
        """Perform semantic search using vector embeddings, falling back cleanly to keyword search if unavailable."""
        if not query or len(query) > 500: raise ValueError("query must be 1-500 characters")
        if not embeddings:
            res = self.keyword_search(query, path, max_results)
            res["mode"] = "keyword_fallback"
            return res

        query_vec = await embeddings.get_embedding(query, model=embedding_model)
        if not query_vec:
            res = self.keyword_search(query, path, max_results)
            res["mode"] = "keyword_fallback"
            return res

        root = self.sandbox.resolve(path, allow_root=True)
        candidates_text: list[dict[str, Any]] = []

        for candidate in root.rglob("*"):
            if len(candidates_text) >= 100: break
            try:
                target = self.sandbox.resolve(candidate)
                if not target.is_file() or target.stat().st_size > self.settings.max_file_read_bytes: continue
                raw = target.read_bytes()
                if b"\x00" in raw[:8192]: continue
                lines = raw.decode("utf-8", errors="replace").splitlines()
                # Group lines into small blocks/paragraphs for embedding
                chunk_size = 5
                for i in range(0, min(len(lines), 50), chunk_size):
                    chunk_lines = lines[i : i + chunk_size]
                    chunk_str = "\n".join(chunk_lines).strip()
                    if chunk_str:
                        candidates_text.append({
                            "path": self.sandbox.display(target),
                            "line": i + 1,
                            "text": chunk_str[:500]
                        })
            except (PermissionError, OSError): continue

        if not candidates_text:
            return {"query": query, "results": [], "truncated": False, "mode": "semantic"}

        chunk_texts = [c["text"] for c in candidates_text]
        doc_vecs = await embeddings.get_embeddings(chunk_texts, model=embedding_model)

        if not doc_vecs or len(doc_vecs) != len(candidates_text):
            res = self.keyword_search(query, path, max_results)
            res["mode"] = "keyword_fallback"
            return res

        scored_results: list[dict[str, Any]] = []
        for cand, vec in zip(candidates_text, doc_vecs):
            score = cosine_similarity(query_vec, vec)
            scored_results.append({**cand, "score": round(score, 4)})

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_results[:min(max_results, 500)]

        return {
            "query": query,
            "results": top_results,
            "truncated": len(scored_results) > max_results,
            "mode": "semantic"
        }
