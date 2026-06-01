import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.campus_seed import CAMPUS_KNOWLEDGE_ITEMS
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate
from app.services.embedding.base import EmbeddingClient
from app.services.embedding.factory import get_embedding_client
from app.services.knowledge_service import create_knowledge


async def seed_knowledge_items(
    db: Session,
    embedding_client: EmbeddingClient,
    *,
    skip_existing: bool = True,
) -> int:
    created_count = 0
    for item in CAMPUS_KNOWLEDGE_ITEMS:
        if skip_existing:
            exists = db.scalar(
                select(KnowledgeBase.id).where(
                    KnowledgeBase.title == item["title"],
                    KnowledgeBase.category == item["category"],
                )
            )
            if exists:
                continue
        await create_knowledge(db, KnowledgeCreate(**item), embedding_client)
        created_count += 1
    return created_count


async def seed_knowledge() -> int:
    settings = get_settings()
    embedding_client = get_embedding_client(settings)
    db = SessionLocal()
    try:
        created_count = await seed_knowledge_items(db, embedding_client, skip_existing=True)
        print(f"Seeded campus knowledge items: {created_count}/{len(CAMPUS_KNOWLEDGE_ITEMS)}")
        return created_count
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_knowledge())
