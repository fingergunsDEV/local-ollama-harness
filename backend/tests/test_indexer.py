import pytest
from unittest.mock import AsyncMock, patch

from app.indexing.embeddings import LocalEmbeddingProvider, chunk_text, cosine_similarity
from app.indexing.indexer import LocalIndexer
from app.tools.search_tools import SearchTools


def test_indexer_honors_gitignore_and_harnessignore(settings, sandbox, store):
    (settings.workspace_root / ".gitignore").write_text("ignored.txt\n")
    (settings.workspace_root / ".harnessignore").write_text("private/\n")
    (settings.workspace_root / "visible.txt").write_text("visible")
    (settings.workspace_root / "ignored.txt").write_text("ignored")
    private = settings.workspace_root / "private"; private.mkdir(); (private / "secret.txt").write_text("secret")
    LocalIndexer(settings, sandbox, store).refresh()
    with store._connect() as conn:
        paths = {row[0] for row in conn.execute("SELECT path FROM file_index")}
    assert "visible.txt" in paths
    assert "ignored.txt" not in paths
    assert "private/secret.txt" not in paths


def test_chunking_and_cosine_similarity():
    text = "Hello world.\nThis is a test of text chunking."
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 0

    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0
    assert cosine_similarity(v1, v3) == 0.0


@pytest.mark.asyncio
async def test_embeddings_generation_and_search(settings, sandbox, store):
    (settings.workspace_root / "doc.txt").write_text("FastAPI python web framework.\nDatabase sqlite integration.")
    indexer = LocalIndexer(settings, sandbox, store)
    indexer.refresh()

    mock_provider = AsyncMock(spec=LocalEmbeddingProvider)
    mock_provider.embed.side_effect = lambda input_data: [[0.5, 0.5, 0.0]] if isinstance(input_data, str) else [[0.5, 0.5, 0.0] for _ in input_data]

    chunks_count = await indexer.generate_embeddings_for_file("doc.txt", mock_provider)
    assert chunks_count > 0

    results = indexer.search_embeddings([0.5, 0.5, 0.0], top_k=5)
    assert len(results) > 0
    assert results[0]["path"] == "doc.txt"
    assert results[0]["score"] == 1.0

    search_tools = SearchTools(settings, sandbox, indexer)
    search_res = await search_tools.semantic_search("FastAPI framework", mock_provider, top_k=2)
    assert len(search_res["results"]) > 0
