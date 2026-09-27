from __future__ import annotations

from pathlib import Path
import pytest

from app.config import Settings
from app.db.session_store import SessionStore
from app.indexing.embeddings import LocalEmbeddings
from app.indexing.indexer import LocalIndexer
from app.safety.sandbox import WorkspaceSandbox
from app.tools.search_tools import SearchTools


@pytest.mark.asyncio
async def test_cosine_similarity():
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    assert LocalEmbeddings.cosine_similarity(vec_a, vec_b) == 1.0
    assert LocalEmbeddings.cosine_similarity(vec_a, vec_c) == 0.0
    assert LocalEmbeddings.cosine_similarity([], vec_a) == 0.0


@pytest.mark.asyncio
async def test_store_and_search_embeddings(tmp_path: Path):
    db_path = tmp_path / "test_store.db"
    store = SessionStore(db_path)

    path = "src/main.py"
    chunks = [
        (0, "def main(): print('hello')", [1.0, 0.0, 0.0]),
        (1, "def helper(): return 42", [0.0, 1.0, 0.0]),
    ]
    store.store_file_embeddings(path, chunks)

    # Search with query vector close to chunk 0
    results = store.search_similar_embeddings([0.9, 0.1, 0.0], top_k=5)
    assert len(results) == 2
    assert results[0]["path"] == "src/main.py"
    assert results[0]["chunk_index"] == 0
    assert "main" in results[0]["content"]


@pytest.mark.asyncio
async def test_semantic_search_tool(tmp_path: Path):
    settings = Settings(workspace_root=tmp_path, sqlite_path=tmp_path / "app.db", audit_log_path=tmp_path / "audit.jsonl")
    sandbox = WorkspaceSandbox(settings)
    store = SessionStore(settings.sqlite_path)

    search_tools = SearchTools(settings, sandbox, store=store)

    store.store_file_embeddings("test.py", [(0, "import math", [0.5, 0.5, 0.0])])

    res = search_tools.semantic_search([0.5, 0.5, 0.0], top_k=1)
    assert "results" in res
    assert len(res["results"]) == 1
    assert res["results"][0]["path"] == "test.py"


class MockEmbedder:
    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        if "hello" in text:
            return [1.0, 0.0]
        return [0.0, 1.0]


@pytest.mark.asyncio
async def test_indexer_embeddings(tmp_path: Path):
    settings = Settings(workspace_root=tmp_path, sqlite_path=tmp_path / "app.db", audit_log_path=tmp_path / "audit.jsonl")
    sandbox = WorkspaceSandbox(settings)
    store = SessionStore(settings.sqlite_path)

    (tmp_path / "sample.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    indexer = LocalIndexer(settings, sandbox, store)
    result = await indexer.index_embeddings(MockEmbedder())

    assert result["embedded_files"] == 1
    assert result["total_chunks"] == 1

    search_res = store.search_similar_embeddings([1.0, 0.0], top_k=1)
    assert len(search_res) == 1
    assert search_res[0]["path"] == "sample.py"
