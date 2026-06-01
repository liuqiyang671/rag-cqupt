from sqlalchemy import text

from app.core.database import Base, engine
from app.models import Feedback, KnowledgeBase, QARecord, User  # noqa: F401


def init_db() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS document_name VARCHAR(255)"))
        connection.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS document_path VARCHAR(500)"))
        connection.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS chunk_index INTEGER"))
        connection.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS chunk_total INTEGER"))
        connection.execute(text("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS chunking_method VARCHAR(50)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_base_document_name ON knowledge_base (document_name)")
        )
        # 新增 qa_records 表的 status 和 updated_at 字段
        connection.execute(
            text("ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_qa_records_status ON qa_records (status)")
        )
        connection.execute(
            text("ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
        )
        connection.execute(
            text("UPDATE qa_records SET updated_at = created_at WHERE updated_at IS NULL")
        )
        connection.execute(
            text("ALTER TABLE qa_records ALTER COLUMN updated_at SET NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE qa_records ALTER COLUMN updated_at SET DEFAULT NOW()")
        )
    print("Database initialized with pgvector extension and application tables.")


if __name__ == "__main__":
    init_db()
