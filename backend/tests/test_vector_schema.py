import pytest

from app.core.ai_errors import VectorSchemaError
from app.services.vector_schema import build_embedding_rebuild_message, validate_embedding_dimensions


def test_build_embedding_rebuild_message_tells_user_how_to_fix_dimension_mismatch():
    message = build_embedding_rebuild_message(configured_dimension=4096, database_dimension=768)

    assert "当前配置需要 4096 维" in message
    assert "数据库 knowledge_base.embedding 是 768 维" in message
    assert "py -3.13 -m app.scripts.rebuild_knowledge_embeddings" in message


def test_validate_embedding_dimensions_raises_rebuild_hint_on_mismatch():
    with pytest.raises(VectorSchemaError, match="需要重新构建知识库向量"):
        validate_embedding_dimensions(configured_dimension=4096, database_dimension=768)
