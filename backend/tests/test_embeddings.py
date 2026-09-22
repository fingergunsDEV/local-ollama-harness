import pytest
from unittest.mock import AsyncMock

from app.indexing.embeddings import LocalEmbeddingService, cosine_similarity


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3), 0.0001) == 0.0

    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0


@pytest.mark.asyncio
async def test_local_embedding_service():
    mock_client = AsyncMock()
    mock_client.embeddings.side_effect = lambda model, prompt: [0.5, 0.5] if "python" in prompt.lower() else [0.1, 0.9]

    service = LocalEmbeddingService(mock_client, default_model="test-embed")
    docs = [
        {"id": 1, "content": "Python backend service code"},
        {"id": 2, "content": "Frontend React component UI"},
    ]

    ranked = await service.rank_by_similarity("Python backend", docs)
    assert len(ranked) == 2
    assert ranked[0]["id"] == 1
    assert ranked[0]["similarity"] > ranked[1]["similarity"]
