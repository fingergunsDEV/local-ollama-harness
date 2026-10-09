from __future__ import annotations

import pytest
from app.indexing.embeddings import LocalEmbeddings
from app.ollama_client import OllamaClient
from app.safety.rate_limiter import OllamaRateLimiter
from app.tools import TOOL_SCHEMAS


def test_stat_file_schema_present():
    names = [tool["function"]["name"] for tool in TOOL_SCHEMAS if "function" in tool]
    assert "stat_file" in names, "stat_file should be exposed in TOOL_SCHEMAS"


@pytest.mark.asyncio
async def test_local_embeddings_embed_query(settings, httpx_mock):
    limiter = OllamaRateLimiter(settings)
    client = OllamaClient(settings, limiter)

    # Mock /api/embed response
    httpx_mock.add_response(
        method="POST",
        url="http://127.0.0.1:11434/api/embed",
        json={"embeddings": [[0.1, 0.2, 0.3]]}
    )

    embeddings_service = LocalEmbeddings(client, default_model="nomic-embed-text")
    query_vector = await embeddings_service.embed_query("hello test")

    assert query_vector == [0.1, 0.2, 0.3]
    await client.close()


@pytest.mark.asyncio
async def test_local_embeddings_embed_documents(settings, httpx_mock):
    limiter = OllamaRateLimiter(settings)
    client = OllamaClient(settings, limiter)

    httpx_mock.add_response(
        method="POST",
        url="http://127.0.0.1:11434/api/embed",
        json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
    )

    embeddings_service = LocalEmbeddings(client)
    doc_vectors = await embeddings_service.embed_documents(["doc1", "doc2"])

    assert doc_vectors == [[0.1, 0.2], [0.3, 0.4]]
    await client.close()
