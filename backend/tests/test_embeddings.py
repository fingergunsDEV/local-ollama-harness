import pytest
from app.indexing.embeddings import LocalEmbeddingEngine, cosine_similarity


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-5
    assert cosine_similarity([], v1) == 0.0


def test_rank_documents(settings, sandbox):
    engine = LocalEmbeddingEngine(settings, None, sandbox)
    query_vec = [1.0, 0.0]
    docs = [
        {"path": "file1.txt", "text": "Hello world", "embedding": [0.9, 0.1]},
        {"path": "file2.txt", "text": "Unrelated topic", "embedding": [0.0, 1.0]},
    ]
    ranked = engine.rank_documents(query_vec, docs, top_k=2)
    assert len(ranked) == 2
    assert ranked[0]["path"] == "file1.txt"
    assert ranked[0]["score"] > ranked[1]["score"]
