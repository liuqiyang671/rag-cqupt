from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.database import Base
from app.models import Feedback, KnowledgeBase, QARecord, User


def _count(db: Session, model: type[object]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_clear_application_data_removes_all_app_table_rows(tmp_path):
    from app.scripts.reset_campus_data import clear_application_data

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.add(User(username="demo", hashed_password="hash", nickname="Demo"))
        db.add(
            KnowledgeBase(
                title="旧知识",
                category="教务服务",
                content="旧知识内容",
                source="旧数据",
                embedding=[0.0] * 4096,
            )
        )
        db.add(QARecord(question="旧问题", answer="旧回答", retrieved_context=[], model_provider="mock"))
        db.commit()
        qa_record = db.scalar(select(QARecord))
        assert qa_record is not None
        db.add(Feedback(qa_record_id=qa_record.id, rating="up", comment="旧反馈"))
        db.commit()

        clear_application_data(db)

        assert _count(db, Feedback) == 0
        assert _count(db, QARecord) == 0
        assert _count(db, KnowledgeBase) == 0
        assert _count(db, User) == 0
    finally:
        db.close()


def test_clear_upload_dir_requires_target_under_allowed_root(tmp_path):
    from app.scripts.reset_campus_data import clear_upload_dir

    allowed_root = tmp_path / "project"
    upload_dir = allowed_root / "backend" / "uploads"
    upload_dir.mkdir(parents=True)
    stored_file = upload_dir / "old.md"
    stored_file.write_text("旧上传", encoding="utf-8")

    removed_count = clear_upload_dir(Settings(UPLOAD_DIR=str(upload_dir)), allowed_root=allowed_root)

    assert removed_count == 1
    assert upload_dir.exists()
    assert list(upload_dir.iterdir()) == []

    outside_upload_dir = tmp_path / "outside" / "uploads"
    outside_upload_dir.mkdir(parents=True)
    (outside_upload_dir / "keep.md").write_text("保留", encoding="utf-8")

    try:
        clear_upload_dir(Settings(UPLOAD_DIR=str(outside_upload_dir)), allowed_root=allowed_root)
    except ValueError as exc:
        assert "Refusing to clear upload directory" in str(exc)
    else:
        raise AssertionError("Expected clear_upload_dir to reject paths outside the allowed root")

    assert (outside_upload_dir / "keep.md").exists()
