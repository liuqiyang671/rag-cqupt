from typing import Optional, Union

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.core.ai_errors import VectorSchemaError


def build_embedding_rebuild_message(configured_dimension: int, database_dimension: Optional[int]) -> str:
    if database_dimension is None:
        current = "未知维度"
    else:
        current = f"{database_dimension} 维"
    return (
        f"需要重新构建知识库向量：当前配置需要 {configured_dimension} 维，"
        f"但数据库 knowledge_base.embedding 是 {current}。"
        "请执行 py -3.13 -m app.scripts.rebuild_knowledge_embeddings 后重启后端。"
    )


def validate_embedding_dimensions(configured_dimension: int, database_dimension: Optional[int]) -> None:
    if database_dimension is None or database_dimension == configured_dimension:
        return
    raise VectorSchemaError(build_embedding_rebuild_message(configured_dimension, database_dimension))


def get_knowledge_embedding_dimension(bind: Union[Connection, Engine]) -> Optional[int]:
    if isinstance(bind, Engine):
        with bind.connect() as connection:
            return get_knowledge_embedding_dimension(connection)

    if bind.dialect.name != "postgresql":
        return None

    exists = bind.execute(text("SELECT to_regclass('knowledge_base')")).scalar()
    if exists is None:
        return None

    return bind.execute(
        text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'knowledge_base'::regclass AND attname = 'embedding'"
        )
    ).scalar()


def ensure_knowledge_embedding_dimension(
    connection: Connection,
    configured_dimension: int,
    *,
    allow_empty_table_migration: bool = True,
) -> None:
    database_dimension = get_knowledge_embedding_dimension(connection)
    if database_dimension is None or database_dimension == configured_dimension:
        return

    row_count = connection.execute(text("SELECT count(1) FROM knowledge_base")).scalar() or 0
    if row_count == 0 and allow_empty_table_migration:
        connection.execute(
            text(f"ALTER TABLE knowledge_base ALTER COLUMN embedding TYPE vector({configured_dimension})")
        )
        return

    validate_embedding_dimensions(configured_dimension, database_dimension)
