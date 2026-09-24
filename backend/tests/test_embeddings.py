import pytest
from app.indexing.embeddings import LocalEmbeddings, cosine_similarity


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)
    assert cosine_similarity([], v1) == 0.0


def test_rank_texts():
    query_vector = [1.0, 0.0]
    texts = [
        ("Doc A", [1.0, 0.0]),
        ("Doc B", [0.0, 1.0]),
        ("Doc C", [0.707, 0.707]),
    ]

    ranked = LocalEmbeddings.rank_texts(query_vector, texts, top_k=2)
    assert len(ranked) == 2
    assert ranked[0]["text"] == "Doc A"
    assert ranked[1]["text"] == "Doc C"
