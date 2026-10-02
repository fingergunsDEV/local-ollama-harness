import pytest
from app.indexing.embeddings import LocalEmbeddingService


def test_cosine_similarity():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert LocalEmbeddingService.cosine_similarity(vec1, vec2) == pytest.approx(1.0)

    vec3 = [0.0, 1.0, 0.0]
    assert LocalEmbeddingService.cosine_similarity(vec1, vec3) == pytest.approx(0.0)

    vec4 = [-1.0, 0.0, 0.0]
    assert LocalEmbeddingService.cosine_similarity(vec1, vec4) == pytest.approx(-1.0)

    assert LocalEmbeddingService.cosine_similarity([], [1.0]) == 0.0
    assert LocalEmbeddingService.cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@pytest.mark.asyncio
async def test_generate_embeddings_empty(settings):
    from app.ollama_client import OllamaClient
    from app.safety.rate_limiter import OllamaRateLimiter

    limiter = OllamaRateLimiter(settings)
    client = OllamaClient(settings, limiter)
    service = LocalEmbeddingService(settings, client)

    res = await service.generate_embeddings("nomic-embed-text", [])
    assert res == []
    await client.close()
