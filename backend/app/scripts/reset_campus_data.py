import argparse
import asyncio
import shutil
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.models import ConversationSession, Feedback, KnowledgeBase, QARecord, User
from app.services.embedding.factory import get_embedding_client
from app.scripts.seed_knowledge import seed_knowledge_items


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _count_files(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        return 1
    if not path.exists():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file() or child.is_symlink())


def clear_upload_dir(settings: Settings, *, allowed_root: Path = PROJECT_ROOT) -> int:
    upload_dir = settings.upload_dir_path.resolve()
    allowed_root = allowed_root.resolve()

    if not upload_dir.is_relative_to(allowed_root):
        raise ValueError(f"Refusing to clear upload directory outside project root: {upload_dir}")

    upload_dir.mkdir(parents=True, exist_ok=True)
    removed_count = 0
    for child in upload_dir.iterdir():
        removed_count += _count_files(child)
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    return removed_count


def clear_application_data(db: Session) -> None:
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            db.execute(
                text(
                    "TRUNCATE TABLE feedback, qa_records, conversation_sessions, "
                    "knowledge_base, users RESTART IDENTITY CASCADE"
                )
            )
        else:
            for model in (Feedback, QARecord, ConversationSession, KnowledgeBase, User):
                db.execute(delete(model))
        db.commit()
    except Exception:
        db.rollback()
        raise


async def reset_campus_data(*, keep_uploads: bool = False) -> tuple[int, int]:
    settings = get_settings()
    removed_upload_count = 0 if keep_uploads else clear_upload_dir(settings)
    embedding_client = get_embedding_client(settings)

    db = SessionLocal()
    try:
        clear_application_data(db)
        seeded_count = await seed_knowledge_items(db, embedding_client, skip_existing=False)
        return seeded_count, removed_upload_count
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear app data and rebuild the campus service knowledge base.")
    parser.add_argument("--keep-uploads", action="store_true", help="Keep files under the configured upload directory.")
    args = parser.parse_args()

    seeded_count, removed_upload_count = asyncio.run(reset_campus_data(keep_uploads=args.keep_uploads))
    print(f"Removed uploaded files: {removed_upload_count}")
    print(f"Seeded campus knowledge items: {seeded_count}")


if __name__ == "__main__":
    main()
