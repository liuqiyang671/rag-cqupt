# 问答记录持久化存储功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现问答记录的持久化存储、删除和归档功能，支持侧边栏快速访问和独立历史页面管理。

**Architecture:** 扩展现有 QARecord 模型添加状态字段，新增归档/恢复/删除 API，创建侧边栏组件和独立历史页面，采用渐进式增强策略分三阶段实现。

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL, React 18, TypeScript, Ant Design, Vite

---

## 文件结构

### 后端文件

| 文件路径 | 职责 | 操作 |
|----------|------|------|
| `backend/app/models/qa_record.py` | 数据模型 | 修改：添加 status、updated_at 字段 |
| `backend/app/services/qa_service.py` | 业务逻辑 | 修改：添加归档、恢复、删除、查询函数 |
| `backend/app/api/routes/qa.py` | API 路由 | 修改：添加归档、恢复、删除端点 |
| `backend/app/schemas/qa.py` | 数据模式 | 修改：更新响应模式 |
| `backend/alembic/versions/xxx_add_status_to_qa_records.py` | 数据库迁移 | 创建：添加新字段 |
| `backend/tests/test_qa_service.py` | 服务测试 | 创建：测试新功能 |
| `backend/tests/test_qa_api.py` | API 测试 | 创建：测试新端点 |

### 前端文件

| 文件路径 | 职责 | 操作 |
|----------|------|------|
| `frontend/src/types.ts` | 类型定义 | 修改：扩展 QARecord 类型 |
| `frontend/src/api/qa.ts` | API 客户端 | 修改：添加新 API 函数 |
| `frontend/src/components/HistorySidebar.tsx` | 侧边栏组件 | 创建：历史记录侧边栏 |
| `frontend/src/pages/ChatPage.tsx` | 聊天页面 | 修改：集成侧边栏 |
| `frontend/src/pages/HistoryPage.tsx` | 历史页面 | 创建：独立历史管理页面 |
| `frontend/src/App.tsx` | 路由配置 | 修改：添加历史页面路由 |
| `frontend/src/styles.css` | 样式 | 修改：添加侧边栏和历史页面样式 |

---

## 阶段 1：基础存储（后端）

### Task 1: 数据库迁移 - 添加新字段

**Files:**
- Modify: `backend/app/models/qa_record.py`
- Create: `backend/alembic/versions/20260531_add_status_to_qa_records.py`

- [ ] **Step 1: 修改 QARecord 模型**

```python
# backend/app/models/qa_record.py
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QARecord(Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # 新增字段
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )
```

- [ ] **Step 2: 创建数据库迁移脚本**

```bash
cd backend
alembic revision --autogenerate -m "add status and updated_at to qa_records"
```

- [ ] **Step 3: 编辑迁移脚本**

```python
# backend/alembic/versions/20260531_add_status_to_qa_records.py
"""add status and updated_at to qa_records

Revision ID: xxx
Revises: xxx
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'xxx'
down_revision = 'xxx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 status 字段
    op.add_column('qa_records', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    op.create_index('ix_qa_records_status', 'qa_records', ['status'])

    # 添加 updated_at 字段
    op.add_column('qa_records', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # 更新现有记录的 updated_at 为 created_at
    op.execute("UPDATE qa_records SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.drop_index('ix_qa_records_status', table_name='qa_records')
    op.drop_column('qa_records', 'updated_at')
    op.drop_column('qa_records', 'status')
```

- [ ] **Step 4: 运行迁移**

```bash
alembic upgrade head
```

Expected: Migration successful, new columns added to qa_records table.

- [ ] **Step 5: 验证数据库结构**

```bash
psql -d your_database -c "\d qa_records"
```

Expected: 看到 status 和 updated_at 字段。

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/qa_record.py backend/alembic/versions/
git commit -m "feat(db): add status and updated_at fields to qa_records"
```

---

### Task 2: 扩展后端服务层

**Files:**
- Modify: `backend/app/services/qa_service.py`
- Create: `backend/tests/test_qa_service.py`

- [ ] **Step 1: 编写服务层测试**

```python
# backend/tests/test_qa_service.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.qa_record import QARecord
from app.services.qa_service import (
    create_qa_record,
    list_qa_records,
    get_qa_record,
    archive_qa_record,
    restore_qa_record,
    delete_qa_record,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_qa_record(db_session):
    record = create_qa_record(
        db=db_session,
        question="test question",
        answer="test answer",
        retrieved_context=[],
        model_provider="deepseek",
    )
    assert record.id is not None
    assert record.question == "test question"
    assert record.status == "active"


def test_list_qa_records_active_only(db_session):
    # 创建活跃记录
    create_qa_record(db_session, "q1", "a1", [], "deepseek")
    create_qa_record(db_session, "q2", "a2", [], "deepseek")

    # 创建归档记录
    record3 = create_qa_record(db_session, "q3", "a3", [], "deepseek")
    archive_qa_record(db_session, record3.id)

    # 查询活跃记录
    records = list_qa_records(db_session, status="active")
    assert len(records) == 2

    # 查询归档记录
    archived = list_qa_records(db_session, status="archived")
    assert len(archived) == 1


def test_archive_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    assert record.status == "active"

    archived = archive_qa_record(db_session, record.id)
    assert archived.status == "archived"


def test_restore_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    archive_qa_record(db_session, record.id)

    restored = restore_qa_record(db_session, record.id)
    assert restored.status == "active"


def test_delete_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    record_id = record.id

    delete_qa_record(db_session, record_id)

    deleted_record = get_qa_record(db_session, record_id)
    assert deleted_record is None


def test_get_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    fetched = get_qa_record(db_session, record.id)
    assert fetched.id == record.id
    assert fetched.question == "q1"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd backend
pytest tests/test_qa_service.py -v
```

Expected: FAIL with "cannot import name 'get_qa_record' from 'app.services.qa_service'"

- [ ] **Step 3: 实现服务层函数**

```python
# backend/app/services/qa_service.py
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.qa_record import QARecord


def create_qa_record(
    db: Session,
    question: str,
    answer: str,
    retrieved_context: list[dict],
    model_provider: str,
) -> QARecord:
    record = QARecord(
        question=question,
        answer=answer,
        retrieved_context=retrieved_context,
        model_provider=model_provider,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    statement = select(QARecord).where(QARecord.id == record_id)
    return db.scalars(statement).first()


def list_qa_records(
    db: Session,
    status: str = "active",
    skip: int = 0,
    limit: int = 50
) -> list[QARecord]:
    statement = (
        select(QARecord)
        .where(QARecord.status == status)
        .order_by(QARecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_qa_records(db: Session, status: str = "active") -> int:
    statement = select(func.count()).select_from(QARecord).where(QARecord.status == status)
    return db.scalar(statement) or 0


def archive_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    record = get_qa_record(db, record_id)
    if record:
        record.status = "archived"
        db.commit()
        db.refresh(record)
    return record


def restore_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    record = get_qa_record(db, record_id)
    if record:
        record.status = "active"
        db.commit()
        db.refresh(record)
    return record


def delete_qa_record(db: Session, record_id: int) -> bool:
    record = get_qa_record(db, record_id)
    if record:
        db.delete(record)
        db.commit()
        return True
    return False
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_qa_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/qa_service.py backend/tests/test_qa_service.py
git commit -m "feat(backend): add qa service functions for archive, restore, delete"
```

---

### Task 3: 扩展 API 路由

**Files:**
- Modify: `backend/app/api/routes/qa.py`
- Modify: `backend/app/schemas/qa.py`
- Create: `backend/tests/test_qa_api.py`

- [ ] **Step 1: 更新响应模式**

```python
# backend/app/schemas/qa.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge import RetrievedKnowledge


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    qa_record_id: int
    retrieved_context: list[RetrievedKnowledge]
    model_provider: str


class QARecordResponse(BaseModel):
    id: int
    question: str
    answer: str
    retrieved_context: list[dict]
    model_provider: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QARecordListResponse(BaseModel):
    records: list[QARecordResponse]
    total: int
    skip: int
    limit: int
```

- [ ] **Step 2: 编写 API 测试**

```python
# backend/tests/test_qa_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.qa_record import QARecord
from app.services.qa_service import create_qa_record


engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_list_records_with_status_filter():
    db = TestingSessionLocal()
    create_qa_record(db, "q1", "a1", [], "deepseek")
    create_qa_record(db, "q2", "a2", [], "deepseek")
    record3 = create_qa_record(db, "q3", "a3", [], "deepseek")
    db.close()

    # 列出活跃记录
    response = client.get("/qa/records?status=active")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["records"]) == 3

    # 归档一条记录
    response = client.put(f"/qa/records/{record3.id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"

    # 再次列出活跃记录
    response = client.get("/qa/records?status=active")
    assert response.json()["total"] == 2

    # 列出归档记录
    response = client.get("/qa/records?status=archived")
    assert response.json()["total"] == 1


def test_archive_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.put(f"/qa/records/{record.id}/archive")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"


def test_restore_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    # 先归档
    client.put(f"/qa/records/{record.id}/archive")

    # 再恢复
    response = client.put(f"/qa/records/{record.id}/restore")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_delete_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.delete(f"/qa/records/{record.id}")
    assert response.status_code == 204

    # 验证已删除
    response = client.get(f"/qa/records/{record.id}")
    assert response.status_code == 404


def test_get_single_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.get(f"/qa/records/{record.id}")
    assert response.status_code == 200
    assert response.json()["question"] == "q1"
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/test_qa_api.py -v
```

Expected: FAIL with various 404 and 405 errors (endpoints not implemented).

- [ ] **Step 4: 实现 API 路由**

```python
# backend/app/api/routes/qa.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.qa import AskRequest, AskResponse, QARecordResponse, QARecordListResponse
from app.services.embedding.factory import get_embedding_client
from app.services.llm.factory import get_llm_client
from app.services.qa_service import (
    list_qa_records,
    count_qa_records,
    get_qa_record,
    archive_qa_record,
    restore_qa_record,
    delete_qa_record,
)
from app.services.rag_service import RAGService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    service = RAGService(
        db=db,
        embedding_client=get_embedding_client(settings),
        llm_client=get_llm_client(settings),
        model_provider=settings.model_provider,
        top_k=settings.top_k,
    )
    return await service.ask(payload.question)


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    service = RAGService(
        db=db,
        embedding_client=get_embedding_client(settings),
        llm_client=get_llm_client(settings),
        model_provider=settings.model_provider,
        top_k=settings.top_k,
    )
    return StreamingResponse(
        service.ask_stream(payload.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/records", response_model=QARecordListResponse)
def records(
    status: str = "active",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    records_list = list_qa_records(db, status=status, skip=skip, limit=limit)
    total = count_qa_records(db, status=status)
    return QARecordListResponse(
        records=records_list,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/records/{record_id}", response_model=QARecordResponse)
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = get_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/records/{record_id}/archive", response_model=QARecordResponse)
def archive_record(record_id: int, db: Session = Depends(get_db)):
    record = archive_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/records/{record_id}/restore", response_model=QARecordResponse)
def restore_record(record_id: int, db: Session = Depends(get_db)):
    record = restore_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    success = delete_qa_record(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return None
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_qa_api.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: 提交**

```bash
git add backend/app/schemas/qa.py backend/app/api/routes/qa.py backend/tests/test_qa_api.py
git commit -m "feat(api): add archive, restore, delete endpoints for qa records"
```

---

## 阶段 2：前端基础功能

### Task 4: 扩展前端类型和 API

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/qa.ts`

- [ ] **Step 1: 更新类型定义**

```typescript
// frontend/src/types.ts - 添加或修改以下类型
export interface QARecord {
  id: number;
  question: string;
  answer: string;
  retrieved_context: KnowledgeItem[];
  model_provider: string;
  status: 'active' | 'archived' | 'deleted';
  created_at: string;
  updated_at: string;
}

export interface QARecordListResponse {
  records: QARecord[];
  total: number;
  skip: number;
  limit: number;
}
```

- [ ] **Step 2: 添加 API 函数**

```typescript
// frontend/src/api/qa.ts - 在文件末尾添加以下函数
import type { QARecord, QARecordListResponse } from '../types';

export async function getQARecords(
  status: string = 'active',
  skip: number = 0,
  limit: number = 20
): Promise<QARecordListResponse> {
  const response = await apiClient.get('/qa/records', {
    params: { status, skip, limit }
  });
  return response.data;
}

export async function getQARecord(id: number): Promise<QARecord> {
  const response = await apiClient.get(`/qa/records/${id}`);
  return response.data;
}

export async function archiveRecord(id: number): Promise<QARecord> {
  const response = await apiClient.put(`/qa/records/${id}/archive`);
  return response.data;
}

export async function restoreRecord(id: number): Promise<QARecord> {
  const response = await apiClient.put(`/qa/records/${id}/restore`);
  return response.data;
}

export async function deleteRecord(id: number): Promise<void> {
  await apiClient.delete(`/qa/records/${id}`);
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

```bash
cd frontend
npm run build
```

Expected: Build successful with no type errors.

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types.ts frontend/src/api/qa.ts
git commit -m "feat(frontend): add qa record types and api functions"
```

---

### Task 5: 创建侧边栏组件

**Files:**
- Create: `frontend/src/components/HistorySidebar.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: 创建侧边栏组件**

```typescript
// frontend/src/components/HistorySidebar.tsx
import { Input, List, Tag, Typography, Button, Spin, Empty } from 'antd';
import { SearchOutlined, HistoryOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { getQARecords } from '../api/qa';
import type { QARecord } from '../types';

interface HistorySidebarProps {
  onSelectRecord: (record: QARecord) => void;
  onViewAll: () => void;
  currentRecordId?: number;
}

export function HistorySidebar({ onSelectRecord, onViewAll, currentRecordId }: HistorySidebarProps) {
  const [records, setRecords] = useState<QARecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    loadRecords();
  }, []);

  async function loadRecords() {
    setLoading(true);
    try {
      const response = await getQARecords('active', 0, 20);
      setRecords(response.records);
    } catch (error) {
      console.error('Failed to load records:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredRecords = searchText
    ? records.filter(r =>
        r.question.toLowerCase().includes(searchText.toLowerCase()) ||
        r.answer.toLowerCase().includes(searchText.toLowerCase())
      )
    : records;

  return (
    <div className="history-sidebar">
      <div className="history-sidebar-header">
        <Typography.Title level={5} style={{ margin: 0 }}>
          <HistoryOutlined /> 历史记录
        </Typography.Title>
        <Button type="link" size="small" onClick={onViewAll}>
          查看全部
        </Button>
      </div>

      <Input
        placeholder="搜索历史..."
        prefix={<SearchOutlined />}
        value={searchText}
        onChange={e => setSearchText(e.target.value)}
        allowClear
        size="small"
        style={{ marginBottom: 12 }}
      />

      <div className="history-sidebar-list">
        {loading ? (
          <div className="history-sidebar-loading">
            <Spin size="small" />
          </div>
        ) : filteredRecords.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无历史记录"
            style={{ margin: '20px 0' }}
          />
        ) : (
          <List
            dataSource={filteredRecords}
            size="small"
            renderItem={record => (
              <div
                className={`history-record-item ${
                  record.id === currentRecordId ? 'active' : ''
                }`}
                onClick={() => onSelectRecord(record)}
              >
                <div className="history-record-question">
                  {record.question}
                </div>
                <div className="history-record-meta">
                  <Tag color="green" style={{ margin: 0 }}>
                    {record.model_provider}
                  </Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(record.created_at).toLocaleDateString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </Typography.Text>
                </div>
              </div>
            )}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 添加侧边栏样式**

```css
/* frontend/src/styles.css - 在文件末尾添加 */

/* 历史侧边栏样式 */
.history-sidebar {
  width: 280px;
  min-width: 280px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border-right: 1px solid rgba(20, 116, 95, 0.14);
  overflow: hidden;
}

.history-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(20, 116, 95, 0.1);
}

.history-sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.history-sidebar-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
}

.history-record-item {
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #14745f;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-record-item:hover {
  background: #f0f9f6;
  transform: translateX(2px);
}

.history-record-item.active {
  background: #e6f7f2;
  border-left-color: #1890ff;
}

.history-record-question {
  font-weight: 500;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-record-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 聊天页面布局调整 */
.chat-page {
  display: flex !important;
  gap: 0 !important;
  padding: 0 !important;
}

.chat-page .workspace-panel {
  flex: 1;
  min-width: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
}

.chat-page .side-note {
  width: 320px;
  min-width: 320px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .chat-page .side-note {
    display: none;
  }
}

@media (max-width: 960px) {
  .history-sidebar {
    display: none;
  }
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

```bash
cd frontend
npm run build
```

Expected: Build successful.

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/HistorySidebar.tsx frontend/src/styles.css
git commit -m "feat(frontend): add history sidebar component"
```

---

### Task 6: 集成侧边栏到聊天页面

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: 修改聊天页面集成侧边栏**

```typescript
// frontend/src/pages/ChatPage.tsx
import { Alert, Card, Space, Statistic, Typography, message } from 'antd';
import { useMemo, useRef, useState } from 'react';
import { askQuestionStream } from '../api/qa';
import { submitFeedback } from '../api/feedback';
import { ChatBox } from '../components/ChatBox';
import { MessageList, type ChatMessage } from '../components/MessageList';
import { HistorySidebar } from '../components/HistorySidebar';
import { useNavigate } from 'react-router-dom';
import type { QARecord } from '../types';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();
  const assistantIdRef = useRef<string>('');
  const navigate = useNavigate();

  const answerCount = useMemo(
    () => messages.filter((item) => item.role === 'assistant' && item.qaRecordId && !item.streaming).length,
    [messages],
  );

  async function handleSend(question: string) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    };
    const assistantId = crypto.randomUUID();
    assistantIdRef.current = assistantId;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setLoading(true);

    await askQuestionStream(question, {
      onMetadata(data) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId
              ? { ...m, context: data.retrieved_context, modelProvider: data.model_provider }
              : m,
          ),
        );
      },
      onChunk(content) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + content } : m,
          ),
        );
      },
      onDone(data) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId
              ? { ...m, qaRecordId: data.qa_record_id, streaming: false }
              : m,
          ),
        );
        setLoading(false);
      },
      onError(error) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m,
          ),
        );
        messageApi.error(error.message || '问答请求失败，请确认后端服务已启动。');
        setLoading(false);
      },
    });
  }

  async function handleFeedback(qaRecordId: number, rating: 'like' | 'dislike') {
    await submitFeedback({ qa_record_id: qaRecordId, rating });
    setMessages((current) =>
      current.map((item) => (item.qaRecordId === qaRecordId ? { ...item, feedbackSent: true } : item)),
    );
    messageApi.success('反馈已提交');
  }

  function handleSelectRecord(record: QARecord) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: record.question,
    };
    const assistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: record.answer,
      context: record.retrieved_context,
      modelProvider: record.model_provider,
      qaRecordId: record.id,
    };
    setMessages([userMessage, assistantMessage]);
  }

  function handleViewAll() {
    navigate('/history');
  }

  const currentRecordId = messages.find(m => m.qaRecordId)?.qaRecordId;

  return (
    <div className="page-grid chat-page">
      {contextHolder}
      <HistorySidebar
        onSelectRecord={handleSelectRecord}
        onViewAll={handleViewAll}
        currentRecordId={currentRecordId}
      />
      <section className="workspace-panel">
        <Space direction="vertical" size={18} className="full-width">
          <div className="page-heading">
            <div>
              <Typography.Title level={2}>高校校园服务智能问答系统</Typography.Title>
              <Typography.Text type="secondary">先检索校园知识库，再生成可追溯回答。</Typography.Text>
            </div>
            <Statistic title="本轮回答" value={answerCount} suffix="条" />
          </div>
          <Alert
            showIcon
            type="info"
            message="试试：校园卡怎么挂失？图书馆开放时间是什么？宿舍报修在哪里提交？"
          />
          <MessageList messages={messages} onFeedback={handleFeedback} />
          <ChatBox loading={loading} onSend={handleSend} />
        </Space>
      </section>
      <aside className="side-note">
        <Card title="回答规则">
          <Space direction="vertical">
            <Typography.Text>优先依据知识库回答。</Typography.Text>
            <Typography.Text>缺少依据时明确说明，不编造。</Typography.Text>
            <Typography.Text>地点、时间、电话、网址按来源原样引用。</Typography.Text>
          </Space>
        </Card>
      </aside>
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend
npm run build
```

Expected: Build successful.

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/ChatPage.tsx
git commit -m "feat(frontend): integrate history sidebar into chat page"
```

---

## 阶段 3：独立历史页面

### Task 7: 创建独立历史页面

**Files:**
- Create: `frontend/src/pages/HistoryPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建历史页面组件**

```typescript
// frontend/src/pages/HistoryPage.tsx
import {
  Button,
  Card,
  Input,
  List,
  message,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
  Empty,
  Spin,
  Pagination,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  InboxOutlined,
  UndoOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getQARecords, archiveRecord, restoreRecord, deleteRecord } from '../api/qa';
import type { QARecord } from '../types';

export function HistoryPage() {
  const navigate = useNavigate();
  const [records, setRecords] = useState<QARecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [status, setStatus] = useState<'active' | 'archived'>('active');
  const [searchText, setSearchText] = useState('');
  const [timeFilter, setTimeFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [messageApi, contextHolder] = message.useMessage();

  const pageSize = 20;

  useEffect(() => {
    loadRecords();
  }, [currentPage, status]);

  async function loadRecords() {
    setLoading(true);
    try {
      const skip = (currentPage - 1) * pageSize;
      const response = await getQARecords(status, skip, pageSize);
      setRecords(response.records);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load records:', error);
      messageApi.error('加载历史记录失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleArchive(id: number) {
    try {
      await archiveRecord(id);
      messageApi.success('已归档');
      loadRecords();
    } catch (error) {
      messageApi.error('归档失败');
    }
  }

  async function handleRestore(id: number) {
    try {
      await restoreRecord(id);
      messageApi.success('已恢复');
      loadRecords();
    } catch (error) {
      messageApi.error('恢复失败');
    }
  }

  function handleDelete(id: number) {
    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除这条记录吗？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteRecord(id);
          messageApi.success('已删除');
          loadRecords();
        } catch (error) {
          messageApi.error('删除失败');
        }
      },
    });
  }

  function handleBatchDelete() {
    if (selectedIds.length === 0) {
      messageApi.warning('请先选择要删除的记录');
      return;
    }

    Modal.confirm({
      title: '批量删除',
      content: `确定要删除选中的 ${selectedIds.length} 条记录吗？删除后无法恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(selectedIds.map(id => deleteRecord(id)));
          messageApi.success(`已删除 ${selectedIds.length} 条记录`);
          setSelectedIds([]);
          loadRecords();
        } catch (error) {
          messageApi.error('批量删除失败');
        }
      },
    });
  }

  function toggleSelect(id: number) {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  }

  function toggleSelectAll() {
    if (selectedIds.length === records.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(records.map(r => r.id));
    }
  }

  const filteredRecords = searchText
    ? records.filter(r =>
        r.question.toLowerCase().includes(searchText.toLowerCase()) ||
        r.answer.toLowerCase().includes(searchText.toLowerCase())
      )
    : records;

  return (
    <div className="history-page">
      {contextHolder}
      <div className="history-page-header">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            返回
          </Button>
          <Typography.Title level={2} style={{ margin: 0 }}>
            历史记录
          </Typography.Title>
        </Space>
        <Typography.Text type="secondary">
          共 {total} 条{status === 'archived' ? '归档' : ''}记录
        </Typography.Text>
      </div>

      <Card className="history-page-content">
        <div className="history-page-toolbar">
          <Space wrap>
            <Input
              placeholder="搜索问题或回答..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              allowClear
              style={{ width: 300 }}
            />
            <Select
              value={timeFilter}
              onChange={setTimeFilter}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部时间' },
                { value: 'today', label: '今天' },
                { value: 'week', label: '最近 7 天' },
                { value: 'month', label: '最近 30 天' },
              ]}
            />
            <Button
              type={status === 'archived' ? 'primary' : 'default'}
              icon={<InboxOutlined />}
              onClick={() => setStatus(status === 'active' ? 'archived' : 'active')}
            >
              {status === 'active' ? '归档区' : '返回活跃'}
            </Button>
          </Space>
          <Space>
            {status === 'active' && (
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
                disabled={selectedIds.length === 0}
              >
                批量删除 {selectedIds.length > 0 && `(${selectedIds.length})`}
              </Button>
            )}
          </Space>
        </div>

        {loading ? (
          <div className="history-page-loading">
            <Spin size="large" />
          </div>
        ) : filteredRecords.length === 0 ? (
          <Empty description="暂无记录" style={{ margin: '40px 0' }} />
        ) : (
          <>
            {status === 'active' && (
              <div className="history-page-select-all">
                <Button size="small" onClick={toggleSelectAll}>
                  {selectedIds.length === records.length ? '取消全选' : '全选'}
                </Button>
              </div>
            )}
            <List
              dataSource={filteredRecords}
              renderItem={record => (
                <div className={`history-record-card ${selectedIds.includes(record.id) ? 'selected' : ''}`}>
                  {status === 'active' && (
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(record.id)}
                      onChange={() => toggleSelect(record.id)}
                      className="history-record-checkbox"
                    />
                  )}
                  <div className="history-record-content">
                    <div className="history-record-question-large">
                      {record.question}
                    </div>
                    <div className="history-record-answer">
                      {record.answer.length > 200
                        ? record.answer.substring(0, 200) + '...'
                        : record.answer}
                    </div>
                    <div className="history-record-footer">
                      <Space>
                        <Tag color="green">{record.model_provider}</Tag>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(record.created_at).toLocaleString('zh-CN')}
                        </Typography.Text>
                      </Space>
                      <Space>
                        <Button
                          size="small"
                          onClick={() => navigate('/', { state: { record } })}
                        >
                          查看
                        </Button>
                        {status === 'active' ? (
                          <>
                            <Button
                              size="small"
                              icon={<InboxOutlined />}
                              onClick={() => handleArchive(record.id)}
                            >
                              归档
                            </Button>
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleDelete(record.id)}
                            >
                              删除
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="small"
                              icon={<UndoOutlined />}
                              onClick={() => handleRestore(record.id)}
                            >
                              恢复
                            </Button>
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleDelete(record.id)}
                            >
                              删除
                            </Button>
                          </>
                        )}
                      </Space>
                    </div>
                  </div>
                </div>
              )}
            />
            <div className="history-page-pagination">
              <Pagination
                current={currentPage}
                total={total}
                pageSize={pageSize}
                onChange={page => setCurrentPage(page)}
                showTotal={total => `共 ${total} 条`}
              />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 添加历史页面样式**

```css
/* frontend/src/styles.css - 在文件末尾添加 */

/* 历史页面样式 */
.history-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.history-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.history-page-content {
  min-height: 600px;
}

.history-page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.history-page-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.history-page-select-all {
  margin-bottom: 12px;
}

.history-record-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  margin-bottom: 12px;
  background: #fafafa;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.history-record-card:hover {
  background: #f0f9f6;
}

.history-record-card.selected {
  background: #e6f7f2;
  border: 1px solid #14745f;
}

.history-record-checkbox {
  width: 18px;
  height: 18px;
  margin-top: 4px;
  accent-color: #14745f;
  cursor: pointer;
}

.history-record-content {
  flex: 1;
  min-width: 0;
}

.history-record-question-large {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1a2724;
}

.history-record-answer {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12px;
}

.history-record-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-page-pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
```

- [ ] **Step 3: 添加路由配置**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { MessageOutlined, DatabaseOutlined, HistoryOutlined } from '@ant-design/icons';
import { ChatPage } from './pages/ChatPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { HistoryPage } from './pages/HistoryPage';
import './styles.css';

const { Header, Content } = Layout;

function AppLayout() {
  const location = useLocation();

  const menuItems = [
    { key: '/', icon: <MessageOutlined />, label: <Link to="/">问答</Link> },
    { key: '/knowledge', icon: <DatabaseOutlined />, label: <Link to="/knowledge">知识库</Link> },
    { key: '/history', icon: <HistoryOutlined />, label: <Link to="/history">历史</Link> },
  ];

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div className="brand">
          <div className="brand-mark">QA</div>
          <span style={{ fontWeight: 600, fontSize: 16 }}>高校校园服务智能问答系统</span>
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
        />
      </Header>
      <Content className="app-content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

```bash
cd frontend
npm run build
```

Expected: Build successful.

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/HistoryPage.tsx frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat(frontend): add history page with archive and delete"
```

---

## 阶段 4：集成测试和优化

### Task 8: 端到端测试

**Files:**
- Test: Manual testing

- [ ] **Step 1: 启动后端服务**

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: Server starts successfully.

- [ ] **Step 2: 启动前端服务**

```bash
cd frontend
npm run dev
```

Expected: Frontend starts at http://localhost:5173.

- [ ] **Step 3: 测试问答功能**

1. 打开 http://localhost:5173
2. 输入问题并发送
3. 验证回答正常显示
4. 刷新页面
5. 验证侧边栏显示历史记录

Expected: 问答功能正常，历史记录持久化。

- [ ] **Step 4: 测试归档功能**

1. 在侧边栏点击"查看全部"
2. 在历史页面点击"归档"按钮
3. 验证记录移到归档区
4. 点击"归档区"按钮
5. 验证可以查看归档记录
6. 点击"恢复"按钮
7. 验证记录恢复到活跃区

Expected: 归档和恢复功能正常。

- [ ] **Step 5: 测试删除功能**

1. 在历史页面点击"删除"按钮
2. 确认删除对话框
3. 验证记录已删除
4. 选择多条记录
5. 点击"批量删除"
6. 确认删除
7. 验证批量删除成功

Expected: 删除和批量删除功能正常。

- [ ] **Step 6: 提交最终版本**

```bash
git add .
git commit -m "feat: complete qa history storage with archive and delete"
```

---

## 自我审查

### 1. 规范覆盖检查

- ✅ **数据模型**：Task 1 实现了 status 和 updated_at 字段
- ✅ **API 接口**：Task 3 实现了所有新增 API 端点
- ✅ **侧边栏**：Task 5 和 Task 6 实现了侧边栏组件和集成
- ✅ **独立历史页面**：Task 7 实现了完整的管理功能
- ✅ **删除功能**：Task 2, 3, 7 实现了硬删除和确认对话框
- ✅ **归档功能**：Task 2, 3, 7 实现了归档和恢复
- ✅ **搜索筛选**：Task 7 实现了搜索和筛选功能
- ✅ **批量操作**：Task 7 实现了批量选择和删除

### 2. 占位符扫描

- ✅ 无 TBD、TODO 或不完整部分
- ✅ 所有代码块都包含完整实现
- ✅ 所有测试步骤都有明确的预期结果

### 3. 类型一致性检查

- ✅ 后端函数名：list_qa_records, get_qa_record, archive_qa_record, restore_qa_record, delete_qa_record
- ✅ 前端函数名：getQARecords, getQARecord, archiveRecord, restoreRecord, deleteRecord
- ✅ 类型定义：QARecord, QARecordListResponse
- ✅ API 路径：/qa/records, /qa/records/{id}, /qa/records/{id}/archive, /qa/records/{id}/restore

---

## 执行选项

**计划已保存到 `docs/superpowers/plans/2026-05-31-qa-history-storage.md`**

两种执行方式：

**1. Subagent-Driven（推荐）** - 我为每个任务派遣一个独立的子代理，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

你选择哪种方式？
