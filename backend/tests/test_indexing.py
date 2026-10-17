import pytest
from app.indexing.embeddings import LocalEmbeddingProvider, chunk_text, cosine_similarity


def test_chunk_text_and_cosine_similarity():
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    chunks = chunk_text(text, chunk_size=15, overlap=5)
    assert len(chunks) > 1

    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    assert abs(cosine_similarity(vec1, vec2) - 1.0) < 1e-5
    assert abs(cosine_similarity(vec1, vec3) - 0.0) < 1e-5
    assert cosine_similarity([], vec1) == 0.0


@pytest.mark.asyncio
async def test_indexer_embeddings_and_search(tmp_path):
    from app.config import Settings
    from app.db.session_store import SessionStore
    from app.indexing.indexer import LocalIndexer
    from app.safety.rate_limiter import OllamaRateLimiter
    from app.safety.sandbox import WorkspaceSandbox
    from app.tools.search_tools import SearchTools

    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    sample_file = ws / "sample.py"
    sample_file.write_text("def hello_world():\n    print('Hello world!')\n")

    settings = Settings(
        workspace_root=ws,
        sqlite_path=tmp_path / "data" / "harness.db",
        audit_log_path=tmp_path / "data" / "audit.jsonl",
    )
    store = SessionStore(settings.sqlite_path)
    sandbox = WorkspaceSandbox(settings)
    limiter = OllamaRateLimiter(settings)
    indexer = LocalIndexer(settings, sandbox, store)

    # Mock provider
    class MockEmbeddingProvider:
        async def embed(self, text):
            if isinstance(text, list):
                return [[0.1, 0.2, 0.3] for _ in text]
            return [[0.1, 0.2, 0.3]]

    provider = MockEmbeddingProvider()

    # Generate embeddings
    count = await indexer.generate_embeddings_for_file("sample.py", provider)
    assert count > 0

    # Search embeddings directly via indexer
    results = indexer.search_embeddings([0.1, 0.2, 0.3], top_k=5)
    assert len(results) == 1
    assert results[0]["path"] == "sample.py"
    assert results[0]["score"] == 1.0

    # Search via SearchTools
    search_tools = SearchTools(settings, sandbox, indexer)
    sem_results = await search_tools.semantic_search("hello world", provider, top_k=5)
    assert len(sem_results["results"]) == 1
    assert sem_results["results"][0]["path"] == "sample.py"
