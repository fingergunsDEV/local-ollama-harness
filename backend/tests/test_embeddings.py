from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.indexing.embeddings import OllamaEmbeddings
from app.indexing.indexer import LocalIndexer
from app.tools.search_tools import SearchTools


@pytest.mark.asyncio
async def test_ollama_embeddings_get_embedding(settings):
    limiter = MagicMock()
    limiter.generation_slot = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
    ollama_client = MagicMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    ollama_client.http.post = AsyncMock(return_value=mock_response)

    embeddings = OllamaEmbeddings(settings, limiter, ollama_client)
    result = await embeddings.get_embedding("hello world")
    assert result == [0.1, 0.2, 0.3]


def test_local_indexer_chunk_text():
    text = "a" * 2500
    chunks = LocalIndexer._chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) == 4
    assert chunks[0] == "a" * 1000


@pytest.mark.asyncio
async def test_semantic_search_cosine_similarity(settings, sandbox, store):
    embeddings_client = MagicMock()
    embeddings_client.get_embedding = AsyncMock(side_effect=lambda text: [1.0, 0.0] if "auth" in text else [0.0, 1.0])

    search_tools = SearchTools(settings, sandbox, store, embeddings_client)

    # Pre-populate file chunks in store
    with store._lock, store._connect() as conn:
        conn.execute("INSERT INTO file_index VALUES('auth.py', 'hash1', 100, 1.0, '2026-01-01')")
        conn.execute("INSERT INTO file_chunks VALUES('c1', 'auth.py', 0, 'authentication logic', '[1.0, 0.0]')")
        conn.execute("INSERT INTO file_chunks VALUES('c2', 'db.py', 0, 'database connection', '[0.0, 1.0]')")

    res = await search_tools.semantic_search("auth query", top_k=1)
    assert len(res["results"]) == 1
    assert res["results"][0]["path"] == "auth.py"
    assert res["results"][0]["score"] == 1.0
