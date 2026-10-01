from app.indexing.indexer import LocalIndexer


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


import pytest
from app.indexing.embeddings import SemanticIndexer, cosine_similarity

class MockOllamaClient:
    async def embeddings(self, model: str, prompt: str) -> list[float]:
        val = float(sum(ord(c) for c in prompt[:10]))
        return [val, val * 2.0, val * 0.5]


def test_cosine_similarity():
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    v3 = [-1.0, -2.0, -3.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == -1.0


@pytest.mark.asyncio
async def test_semantic_indexer_index_and_search(settings, sandbox, store):
    mock_client = MockOllamaClient()
    indexer = SemanticIndexer(settings, sandbox, store, mock_client)

    file_path = settings.workspace_root / "sample.txt"
    file_path.write_text("This is a sample document for testing semantic indexer.")

    indexed_chunks = await indexer.index_file("sample.txt", "llama3.1:8b")
    assert indexed_chunks > 0

    results = await indexer.search("sample document", "llama3.1:8b", top_k=5)
    assert len(results) > 0
    assert results[0]["path"] == "sample.txt"
