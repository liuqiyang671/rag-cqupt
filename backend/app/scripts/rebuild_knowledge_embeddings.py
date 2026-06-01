import asyncio
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.knowledge import KnowledgeBase
from app.services.embedding.base import EmbeddingClient
from app.services.embedding.factory import get_embedding_client
from app.services.knowledge_service import knowledge_embedding_text
from app.services.vector_schema import get_knowledge_embedding_dimension


@dataclass
class KnowledgeSnapshot:
    id: int
    title: str
    category: str
    content: str
    source: str
    document_name: str | None
    document_path: str | None
    chunk_index: int | None
    chunk_total: int | None
    chunking_method: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class EmbeddedKnowledgeSnapshot:
    snapshot: KnowledgeSnapshot
    embedding: list[float]


def snapshot_knowledge_items(db: Session) -> list[KnowledgeSnapshot]:
    rows = db.query(KnowledgeBase).order_by(KnowledgeBase.id.asc()).all()
    return [
        KnowledgeSnapshot(
            id=row.id,
            title=row.title,
            category=row.category,
            content=row.content,
            source=row.source,
            document_name=row.document_name,
            document_path=row.document_path,
            chunk_index=row.chunk_index,
            chunk_total=row.chunk_total,
            chunking_method=row.chunking_method,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


async def embed_snapshots(
    snapshots: list[KnowledgeSnapshot],
    embedding_client: EmbeddingClient,
) -> list[EmbeddedKnowledgeSnapshot]:
    embedded: list[EmbeddedKnowledgeSnapshot] = []
    total = len(snapshots)
    for index, snapshot in enumerate(snapshots, start=1):
        text_to_embed = knowledge_embedding_text(
            snapshot.title,
            snapshot.category,
            snapshot.content,
            snapshot.source,
        )
        embedding = await embedding_client.embed(text_to_embed)
        embedded.append(EmbeddedKnowledgeSnapshot(snapshot=snapshot, embedding=embedding))
        if index == 1 or index == total or index % 10 == 0:
            print(f"Embedded knowledge items: {index}/{total}")
    return embedded


def sync_embedding_column(dimension: int) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        current_dimension = get_knowledge_embedding_dimension(connection)
        if connection.dialect.name == "postgresql" and current_dimension != dimension:
            connection.execute(text("TRUNCATE TABLE knowledge_base RESTART IDENTITY"))
            connection.execute(text(f"ALTER TABLE knowledge_base ALTER COLUMN embedding TYPE vector({dimension})"))
        elif connection.dialect.name == "postgresql":
            connection.execute(text("TRUNCATE TABLE knowledge_base RESTART IDENTITY"))


def restore_knowledge_items(db: Session, embedded_items: list[EmbeddedKnowledgeSnapshot]) -> None:
    try:
        for item in embedded_items:
            snapshot = item.snapshot
            db.add(
                KnowledgeBase(
                    id=snapshot.id,
                    title=snapshot.title,
                    category=snapshot.category,
                    content=snapshot.content,
                    source=snapshot.source,
                    document_name=snapshot.document_name,
                    document_path=snapshot.document_path,
                    chunk_index=snapshot.chunk_index,
                    chunk_total=snapshot.chunk_total,
                    chunking_method=snapshot.chunking_method,
                    embedding=item.embedding,
                    created_at=snapshot.created_at,
                    updated_at=snapshot.updated_at,
                )
            )
        db.commit()
        if embedded_items and db.get_bind().dialect.name == "postgresql":
            max_id = max(item.snapshot.id for item in embedded_items)
            db.execute(text("SELECT setval(pg_get_serial_sequence('knowledge_base', 'id'), :max_id, true)"), {"max_id": max_id})
            db.commit()
    except Exception:
        db.rollback()
        raise


async def rebuild_knowledge_embeddings() -> int:
    settings = get_settings()
    embedding_client = get_embedding_client(settings)

    db = SessionLocal()
    try:
        snapshots = snapshot_knowledge_items(db)
    finally:
        db.close()

    if not snapshots:
        print("No knowledge items found; only synchronizing embedding column dimension.")
        sync_embedding_column(settings.embedding_dimension)
        return 0

    print(f"Rebuilding {len(snapshots)} knowledge embeddings at {settings.embedding_dimension} dimensions.")
    embedded_items = await embed_snapshots(snapshots, embedding_client)
    sync_embedding_column(settings.embedding_dimension)

    db = SessionLocal()
    try:
        restore_knowledge_items(db, embedded_items)
    finally:
        db.close()
    return len(embedded_items)


def main() -> None:
    rebuilt_count = asyncio.run(rebuild_knowledge_embeddings())
    print(f"Rebuilt knowledge embeddings: {rebuilt_count}")


if __name__ == "__main__":
    main()
