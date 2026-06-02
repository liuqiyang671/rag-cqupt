from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.data.campus_seed import CAMPUS_KNOWLEDGE_CATEGORIES, CAMPUS_KNOWLEDGE_ITEMS
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate
from app.services.embedding.base import EmbeddingClient
from app.services.embedding.factory import get_embedding_client
from app.services.knowledge_service import knowledge_embedding_text
from app.services.vector_schema import get_knowledge_embedding_dimension, validate_embedding_dimensions


@dataclass(frozen=True)
class LoadCompleteRagDataResult:
    created_count: int
    updated_count: int
    total_count: int
    category_counts: dict[str, int]


def count_knowledge_by_category(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id)).group_by(KnowledgeBase.category)
    ).all()
    return {category: count for category, count in rows}


async def _build_embedding(
    db: Session,
    embedding_client: EmbeddingClient,
    payload: KnowledgeCreate,
) -> list[float]:
    embedding = await embedding_client.embed(
        knowledge_embedding_text(payload.title, payload.category, payload.content, payload.source)
    )
    validate_embedding_dimensions(
        configured_dimension=len(embedding),
        database_dimension=get_knowledge_embedding_dimension(db.get_bind()),
    )
    return embedding


async def load_complete_rag_data(
    db: Session,
    embedding_client: EmbeddingClient,
    *,
    reset_knowledge: bool = False,
) -> LoadCompleteRagDataResult:
    created_count = 0
    updated_count = 0

    try:
        if reset_knowledge:
            db.execute(delete(KnowledgeBase))
            db.flush()

        for item in CAMPUS_KNOWLEDGE_ITEMS:
            payload = KnowledgeCreate(**item)
            embedding = await _build_embedding(db, embedding_client, payload)
            existing = None
            if not reset_knowledge:
                existing = db.scalar(
                    select(KnowledgeBase).where(
                        KnowledgeBase.title == payload.title,
                        KnowledgeBase.category == payload.category,
                    )
                )

            if existing is None:
                db.add(KnowledgeBase(**payload.model_dump(), embedding=embedding))
                created_count += 1
            else:
                for key, value in payload.model_dump().items():
                    setattr(existing, key, value)
                existing.embedding = embedding
                db.add(existing)
                updated_count += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    total_count = db.scalar(select(func.count()).select_from(KnowledgeBase)) or 0
    return LoadCompleteRagDataResult(
        created_count=created_count,
        updated_count=updated_count,
        total_count=total_count,
        category_counts=count_knowledge_by_category(db),
    )


async def run_load_complete_rag_data(*, reset_knowledge: bool = False) -> LoadCompleteRagDataResult:
    settings = get_settings()
    embedding_client = get_embedding_client(settings)
    db = SessionLocal()
    try:
        return await load_complete_rag_data(db, embedding_client, reset_knowledge=reset_knowledge)
    finally:
        db.close()


def _print_result(result: LoadCompleteRagDataResult) -> None:
    print(f"Created knowledge items: {result.created_count}")
    print(f"Updated knowledge items: {result.updated_count}")
    print(f"Total knowledge items in database: {result.total_count}")
    print("Category counts:")
    for category in CAMPUS_KNOWLEDGE_CATEGORIES:
        print(f"  - {category}: {result.category_counts.get(category, 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load the complete campus service RAG knowledge base.")
    parser.add_argument(
        "--reset-knowledge",
        action="store_true",
        help="Delete existing knowledge_base rows before loading the complete campus data set.",
    )
    args = parser.parse_args()

    result = asyncio.run(run_load_complete_rag_data(reset_knowledge=args.reset_knowledge))
    _print_result(result)


if __name__ == "__main__":
    main()
