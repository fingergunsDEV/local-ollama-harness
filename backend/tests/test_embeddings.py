import pytest
from app.indexing.embeddings import cosine_similarity, LocalEmbeddings


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)
    assert cosine_similarity([], v1) == 0.0


@pytest.mark.asyncio
async def test_local_embeddings(mocker=None):
    class MockOllamaClient:
        async def embeddings(self, model: str, prompt: str):
            return [0.1, 0.2, 0.3]

    client = MockOllamaClient()
    embeddings = LocalEmbeddings(client)
    res = await embeddings.embed_text("hello world")
    assert res == [0.1, 0.2, 0.3]
