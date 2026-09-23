from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.indexing.embeddings import OllamaEmbeddings
from app.ollama_client import OllamaUnavailable


@pytest.mark.asyncio
async def test_embed_batch_success_api_embed():
    mock_client = MagicMock()
    mock_client.limiter.generation_slot = AsyncMock(return_value=AsyncMock())

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}

    mock_client.http.post = AsyncMock(return_value=mock_response)

    embedder = OllamaEmbeddings(mock_client, default_model="nomic-embed-text")
    res = await embedder.embed_batch(["hello", "world"])

    assert res == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.http.post.assert_called_once_with("/api/embed", json={"model": "nomic-embed-text", "input": ["hello", "world"]})


@pytest.mark.asyncio
async def test_embed_text_single():
    mock_client = MagicMock()
    mock_client.limiter.generation_slot = AsyncMock(return_value=AsyncMock())

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

    mock_client.http.post = AsyncMock(return_value=mock_response)

    embedder = OllamaEmbeddings(mock_client)
    res = await embedder.embed_text("test string")

    assert res == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_fallback_to_api_embeddings():
    mock_client = MagicMock()
    mock_client.limiter.generation_slot = AsyncMock(return_value=AsyncMock())

    # Response 1 for /api/embed (404 Not Found)
    res_embed_404 = MagicMock()
    res_embed_404.status_code = 404

    # Response 2 for /api/embeddings
    res_embeddings_ok = MagicMock()
    res_embeddings_ok.status_code = 200
    res_embeddings_ok.raise_for_status = MagicMock()
    res_embeddings_ok.json.return_value = {"embedding": [0.9, 0.8, 0.7]}

    mock_client.http.post = AsyncMock(side_effect=[res_embed_404, res_embeddings_ok])

    embedder = OllamaEmbeddings(mock_client)
    res = await embedder.embed_batch(["test"])

    assert res == [[0.9, 0.8, 0.7]]


@pytest.mark.asyncio
async def test_embed_error_handling():
    mock_client = MagicMock()
    mock_client.limiter.generation_slot = AsyncMock(return_value=AsyncMock())
    mock_client.http.post = AsyncMock(side_effect=httpx.HTTPError("Network failure"))

    embedder = OllamaEmbeddings(mock_client)
    with pytest.raises(OllamaUnavailable):
        await embedder.embed_text("fail")
