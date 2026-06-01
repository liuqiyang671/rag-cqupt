from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services.embedding.base import EmbeddingClient


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
    item = KnowledgeBase(**payload.model_dump(), embedding=embedding)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_knowledge(
    db: Session,
    category: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[KnowledgeBase]:
    statement = select(KnowledgeBase)
    if category:
        statement = statement.where(KnowledgeBase.category == category)
    statement = statement.order_by(KnowledgeBase.updated_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_knowledge(db: Session, knowledge_id: int) -> KnowledgeBase | None:
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

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_knowledge(db: Session, item: KnowledgeBase) -> None:
    db.delete(item)
    db.commit()


def retrieve_similar_knowledge(
    db: Session,
    query_embedding: list[float],
    top_k: int,
) -> list[KnowledgeBase]:
    statement = (
        select(KnowledgeBase)
        .order_by(KnowledgeBase.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    return list(db.scalars(statement).all())

