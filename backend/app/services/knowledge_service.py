from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.campus_seed import CAMPUS_KNOWLEDGE_CATEGORIES
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services.embedding.base import EmbeddingClient
from app.services.vector_schema import get_knowledge_embedding_dimension, validate_embedding_dimensions


def knowledge_embedding_text(title: str, category: str, content: str, source: str) -> str:
    return f"{title}\n分类：{category}\n来源：{source}\n{content}"


async def create_knowledge(
    db: Session,
    payload: KnowledgeCreate,
    embedding_client: EmbeddingClient,
) -> KnowledgeBase:
    embedding = await embedding_client.embed(
        knowledge_embedding_text(payload.title, payload.category, payload.content, payload.source)
    )
    validate_embedding_dimensions(
        configured_dimension=len(embedding),
        database_dimension=get_knowledge_embedding_dimension(db.get_bind()),
    )
    item = KnowledgeBase(**payload.model_dump(), embedding=embedding)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_knowledge(
    db: Session,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[KnowledgeBase]:
    statement = select(KnowledgeBase)
    if category:
        statement = statement.where(KnowledgeBase.category == category)
    statement = statement.order_by(KnowledgeBase.updated_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_knowledge_category_stats(db: Session) -> dict:
    item_rows = db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id)).group_by(KnowledgeBase.category)
    ).all()
    document_rows = db.execute(
        select(KnowledgeBase.category, func.count(func.distinct(KnowledgeBase.document_name)))
        .where(KnowledgeBase.document_name.is_not(None))
        .group_by(KnowledgeBase.category)
    ).all()
    chunk_rows = db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id))
        .where(KnowledgeBase.document_name.is_not(None))
        .group_by(KnowledgeBase.category)
    ).all()

    item_counts = {category: count for category, count in item_rows}
    document_counts = {category: count for category, count in document_rows}
    chunk_counts = {category: count for category, count in chunk_rows}
    known_categories = set(CAMPUS_KNOWLEDGE_CATEGORIES)
    known_categories.update(item_counts)

    category_order = {category: index for index, category in enumerate(CAMPUS_KNOWLEDGE_CATEGORIES)}
    categories = [
        {
            "category": category,
            "item_count": item_counts.get(category, 0),
            "document_count": document_counts.get(category, 0),
            "chunk_count": chunk_counts.get(category, 0),
        }
        for category in sorted(known_categories, key=lambda value: (category_order.get(value, 10_000), value))
    ]
    return {"categories": categories, "total_items": sum(item_counts.values())}


def get_knowledge(db: Session, knowledge_id: int) -> Optional[KnowledgeBase]:
    return db.get(KnowledgeBase, knowledge_id)


async def update_knowledge(
    db: Session,
    item: KnowledgeBase,
    payload: KnowledgeUpdate,
    embedding_client: EmbeddingClient,
) -> KnowledgeBase:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(item, key, value)

    if any(key in updates for key in ("title", "category", "content", "source")):
        item.embedding = await embedding_client.embed(
            knowledge_embedding_text(item.title, item.category, item.content, item.source)
        )
        validate_embedding_dimensions(
            configured_dimension=len(item.embedding),
            database_dimension=get_knowledge_embedding_dimension(db.get_bind()),
        )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_knowledge(db: Session, item: KnowledgeBase) -> None:
    db.delete(item)
    db.commit()


def retrieve_similar_knowledge(
    db: Session,
    query_embedding: List[float],
    top_k: int,
) -> List[KnowledgeBase]:
    validate_embedding_dimensions(
        configured_dimension=len(query_embedding),
        database_dimension=get_knowledge_embedding_dimension(db.get_bind()),
    )
    statement = (
        select(KnowledgeBase)
        .order_by(KnowledgeBase.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    return list(db.scalars(statement).all())
