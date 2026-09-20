from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.indexing.embeddings import OllamaEmbeddings, cosine_similarity
from app.ollama_client import OllamaUnavailable
from app.tools.search_tools import SearchTools


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0
    assert cosine_similarity(v1, v3) == 0.0
    assert cosine_similarity([], v1) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@pytest.mark.asyncio
async def test_ollama_embeddings_success():
    client = AsyncMock()
    client.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    embedder = OllamaEmbeddings(client, default_model="test-embed")

    vecs = await embedder.get_embeddings(["hello", "world"])
    assert len(vecs) == 2
    assert vecs[0] == [0.1, 0.2, 0.3]
    client.embed.assert_called_once_with("test-embed", ["hello", "world"])

    single_vec = await embedder.get_embedding("hello")
    assert len(single_vec) == 3


@pytest.mark.asyncio
async def test_ollama_embeddings_fallback():
    client = AsyncMock()
    client.embed = AsyncMock(side_effect=OllamaUnavailable("Offline"))
    embedder = OllamaEmbeddings(client)

    vecs = await embedder.get_embeddings(["hello"])
    assert vecs == []

    vec = await embedder.get_embedding("hello")
    assert vec == []


@pytest.mark.asyncio
async def test_semantic_search_fallback(settings, sandbox):
    search = SearchTools(settings, sandbox)

    # Write a dummy file to workspace
    file_path = sandbox.root / "sample.txt"
    file_path.write_text("The quick brown fox jumps over the lazy dog", encoding="utf-8")

    # With no embeddings instance, falls back to keyword search
    res = await search.semantic_search("fox")
    assert res["mode"] == "keyword_fallback"
    assert len(res["results"]) > 0
    assert res["results"][0]["path"] == "sample.txt"


@pytest.mark.asyncio
async def test_semantic_search_success(settings, sandbox):
    search = SearchTools(settings, sandbox)

    file_path = sandbox.root / "sample.txt"
    file_path.write_text("Artificial Intelligence and Machine Learning", encoding="utf-8")

    client = AsyncMock()
    # Mock query embedding and chunk embedding
    client.embed = AsyncMock(side_effect=lambda model, texts: [[0.5, 0.5, 0.5]] * len(texts))
    embedder = OllamaEmbeddings(client)

    res = await search.semantic_search("AI", embeddings=embedder)
    assert res["mode"] == "semantic"
    assert len(res["results"]) > 0
    assert res["results"][0]["score"] == 1.0
