from app.services.embedding.mock_embedding import MockEmbeddingClient


def test_mock_embedding_is_deterministic_and_dimensioned():
    client = MockEmbeddingClient(dimension=16)

    first = client.embed_sync("校园卡怎么挂失？")
    second = client.embed_sync("校园卡怎么挂失？")
    other = client.embed_sync("图书馆开放时间是什么？")

    assert len(first) == 16
    assert first == second
    assert first != other
    assert all(isinstance(value, float) for value in first)

