import pytest
from unittest.mock import AsyncMock, MagicMock

from app.indexing.embeddings import EmbeddingManager, cosine_similarity
from app.tools.search_tools import SearchTools


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)

    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], [0.0]) == 0.0


def test_regex_search(settings, sandbox):
    (sandbox.root / "sample.txt").write_text("hello world\npython 3.12\nfoo bar 123", encoding="utf-8")
    search_tools = SearchTools(settings, sandbox)

    res = search_tools.regex_search(r"python \d+\.\d+", path=".")
    assert len(res["results"]) == 1
    assert res["results"][0]["path"] == "sample.txt"
    assert res["results"][0]["line"] == 2

    res_glob = search_tools.regex_search(r"world", file_pattern="*.txt")
    assert len(res_glob["results"]) == 1


@pytest.mark.asyncio
async def test_embedding_manager_and_semantic_search(settings, store):
    mock_client = AsyncMock()
    mock_client.embed.return_value = [[0.5, 0.5, 0.0]]

    manager = EmbeddingManager(settings, store, mock_client)
    await manager.store_chunk_embedding("test.py", 0, "def foo(): pass", "nomic-embed-text")

    results = await manager.search("foo function", "nomic-embed-text", limit=5)
    assert len(results) == 1
    assert results[0]["path"] == "test.py"
    assert results[0]["score"] == pytest.approx(1.0)


def test_stats_endpoints(store):
    sess = store.create_session("llama3.1", False, "/tmp")
    store.add_message(sess["id"], "user", "hello", token_count=10)
    store.add_message(sess["id"], "assistant", "hi", token_count=5)

    stats = store.session_stats(sess["id"])
    assert stats["message_count"] == 2
    assert stats["total_tokens"] == 15

    g_stats = store.global_stats()
    assert g_stats["total_sessions"] >= 1
    assert g_stats["total_messages"] >= 2
    assert g_stats["total_tokens"] >= 15
