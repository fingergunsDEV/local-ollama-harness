from unittest.mock import AsyncMock

import pytest

from app.db.session_store import SessionStore
from app.indexing.embeddings import OllamaEmbedder
from app.safety.sandbox import WorkspaceSandbox


@pytest.mark.asyncio
async def test_embedder_and_store_search(settings, sandbox, store):
    client_mock = AsyncMock()
    client_mock.embed.return_value = [[0.1, 0.2, 0.3]]

    embedder = OllamaEmbedder(settings, client_mock, store, sandbox)

    test_file = settings.workspace_root / "code.py"
    test_file.write_text("def hello(): return 'world'\n", encoding="utf-8")

    res = await embedder.index_file("llama3", "code.py", chunk_size=100)
    assert res["chunks_indexed"] == 1

    search_res = store.search_embeddings([0.1, 0.2, 0.3], top_k=1)
    assert len(search_res) == 1
    assert search_res[0]["path"] == "code.py"
    assert search_res[0]["score"] == 1.0


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert SessionStore._cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert SessionStore._cosine_similarity(v1, v3) == pytest.approx(0.0)
