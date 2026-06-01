# 问答记录持久化存储功能设计文档

**日期：** 2026-05-31
**状态：** 已批准
**版本：** 1.0

---

## 1. 概述

### 1.1 背景

当前系统的问答记录存储在数据库中，但前端页面刷新或离开后，聊天记录会丢失。用户需要：
- 持久化存储问答记录
- 查看历史记录
- 删除不需要的记录
- 归档重要记录

### 1.2 目标

- 页面加载时自动恢复历史问答记录
- 提供侧边栏快速访问最近记录
- 提供独立历史页面进行完整管理
- 支持删除和归档功能

### 1.3 范围

**阶段 1（核心功能）：**
- 页面加载时恢复历史记录
- 聊天页面侧边栏显示最近 20 条记录
- 点击侧边栏记录可查看详情

**阶段 2（管理功能）：**
- 删除功能（确认对话框后硬删除）
- 归档功能（移到归档区）
- 独立历史页面（完整列表、搜索、筛选）

**阶段 3（高级功能）：**
- 批量操作
- 导出功能
- 更多筛选选项

---

## 2. 用户需求

### 2.1 用户故事

1. 作为用户，我希望刷新页面后仍能看到之前的问答记录，这样我不会丢失重要信息。
2. 作为用户，我希望能快速访问最近的问答记录，这样我可以继续之前的对话。
3. 作为用户，我希望能删除不需要的记录，这样我的历史列表保持整洁。
4. 作为用户，我希望能归档重要记录，这样我可以将它们与普通记录分开管理。

### 2.2 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 历史界面布局 | 混合模式（侧边栏 + 独立页面） | 既提供快速访问，又提供完整管理 |
| 归档行为 | 移到归档文件夹 | 清晰的物理分离，用户容易理解 |
| 删除行为 | 确认后硬删除 | 实现简单，数据干净 |
| 用户数据隔离 | 全局共享 | 当前无用户系统，保持简单 |
| 实现阶段 | 渐进式增强 | 风险低，可逐步验证 |

---

## 3. 系统设计

### 3.1 数据模型

#### 现有模型

```python
class QARecord(Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
```

#### 扩展字段

```python
class QARecord(Base):
    __tablename__ = "qa_records"

    # 现有字段保持不变
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

#### 状态流转

```
active (活跃) → archived (归档) → deleted (硬删除)
     ↑                                  |
     |__________________________________|
              (恢复)
```

- **active**：正常状态，显示在主列表
- **archived**：归档状态，移到归档区，可恢复
- **deleted**：硬删除，从数据库中移除

### 3.2 API 设计

#### 现有 API（修改）

```python
# GET /qa/records
# 新增 status 参数支持按状态筛选
@router.get("/records", response_model=list[QARecordResponse])
def records(
    status: str = "active",  # 新增参数
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return list_qa_records(db, status=status, skip=skip, limit=limit)
```

#### 新增 API

```python
# GET /qa/records/{id}
# 获取单条记录详情
@router.get("/records/{record_id}", response_model=QARecordResponse)
def get_record(record_id: int, db: Session = Depends(get_db)):
    return get_qa_record(db, record_id)

# PUT /qa/records/{id}/archive
# 归档记录
@router.put("/records/{record_id}/archive", response_model=QARecordResponse)
def archive_record(record_id: int, db: Session = Depends(get_db)):
    return update_qa_record_status(db, record_id, "archived")

# PUT /qa/records/{id}/restore
# 恢复归档记录
@router.put("/records/{record_id}/restore", response_model=QARecordResponse)
def restore_record(record_id: int, db: Session = Depends(get_db)):
    return update_qa_record_status(db, record_id, "active")

# DELETE /qa/records/{id}
# 硬删除记录
@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    delete_qa_record(db, record_id)
    return None
```

#### 响应格式

```json
// GET /qa/records?status=active&skip=0&limit=20
{
  "records": [
    {
      "id": 1,
      "question": "校园卡怎么挂失？",
      "answer": "校园卡挂失可以通过以下方式...",
      "retrieved_context": [...],
      "model_provider": "deepseek",
      "status": "active",
      "created_at": "2026-05-31T10:30:00Z",
      "updated_at": "2026-05-31T10:30:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}

// PUT /qa/records/1/archive
{
  "id": 1,
  "question": "校园卡怎么挂失？",
  "answer": "校园卡挂失可以通过以下方式...",
  "retrieved_context": [...],
  "model_provider": "deepseek",
  "status": "archived",
  "created_at": "2026-05-31T10:30:00Z",
  "updated_at": "2026-05-31T11:00:00Z"
}

// DELETE /qa/records/1
// 响应：204 No Content
```

### 3.3 前端设计

#### 3.3.1 聊天页面侧边栏

**布局：**
- 左侧 280px 宽度的侧边栏
- 固定定位，不随聊天区域滚动
- 可折叠（屏幕宽度 < 960px 时自动隐藏）

**功能：**
- 显示最近 20 条活跃记录
- 快速搜索框（按问题内容搜索）
- 点击记录加载到聊天区域
- "查看全部"按钮跳转到独立历史页面
- 高亮当前正在查看的记录

**样式：**
- 使用项目现有的绿色主题（#14745f）
- 记录卡片带左侧边框指示器
- 悬停效果和点击反馈

#### 3.3.2 独立历史页面

**布局：**
- 路由：`/history`
- 响应式网格布局
- 顶部操作栏 + 搜索筛选 + 记录列表 + 分页

**功能：**
- 完整的历史记录列表（分页显示）
- 搜索框（搜索问题和回答内容）
- 时间筛选（全部时间、今天、最近 7 天、最近 30 天）
- 模型筛选（按 model_provider 筛选）
- 每条记录的操作按钮：查看、归档、删除
- 批量选择和批量删除
- 归档区入口（显示归档数量）

**交互：**
- 删除前弹出确认对话框
- 归档操作直接执行（显示成功提示）
- 批量操作需要先选择记录

---

## 4. 实现阶段

### 阶段 1：基础存储（预计 2-3 天）

**后端：**
1. 修改 `QARecord` 模型，添加 `status` 和 `updated_at` 字段
2. 创建数据库迁移脚本
3. 修改 `list_qa_records` 服务，支持按状态筛选
4. 测试现有功能不受影响

**前端：**
1. 创建 `HistorySidebar` 组件
2. 在 `ChatPage` 中集成侧边栏
3. 修改 `ChatPage`，页面加载时从 API 恢复历史记录
4. 点击侧边栏记录加载到聊天区域
5. 添加侧边栏样式

### 阶段 2：管理功能（预计 3-4 天）

**后端：**
1. 实现 `archive_record` API
2. 实现 `restore_record` API
3. 实现 `delete_record` API
4. 实现 `get_record` API
5. 编写单元测试

**前端：**
1. 创建独立历史页面（`HistoryPage`）
2. 实现搜索和筛选功能
3. 实现归档、删除操作
4. 实现确认对话框
5. 添加路由配置

### 阶段 3：高级功能（预计 2-3 天）

**后端：**
1. 实现批量删除 API
2. 优化查询性能（添加索引）

**前端：**
1. 实现批量选择和批量删除
2. 实现导出功能
3. 优化移动端体验
4. 添加加载状态和错误处理

---

## 5. 技术细节

### 5.1 数据库迁移

```sql
-- 添加 status 字段
ALTER TABLE qa_records
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active';

-- 添加索引
CREATE INDEX idx_qa_records_status ON qa_records(status);

-- 添加 updated_at 字段
ALTER TABLE qa_records
ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- 更新现有记录的 updated_at 为 created_at
UPDATE qa_records SET updated_at = created_at WHERE updated_at IS NULL;
```

### 5.2 前端状态管理

```typescript
// types.ts - 扩展 QARecord 类型
interface QARecord {
  id: number;
  question: string;
  answer: string;
  retrieved_context: KnowledgeItem[];
  model_provider: string;
  status: 'active' | 'archived' | 'deleted';
  created_at: string;
  updated_at: string;
}

// api/qa.ts - 新增 API 函数
export async function getQARecords(
  status: string = 'active',
  skip: number = 0,
  limit: number = 20
): Promise<{ records: QARecord[]; total: number }> {
  const response = await apiClient.get('/qa/records', {
    params: { status, skip, limit }
  });
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

### 5.3 组件结构

```
frontend/src/
├── components/
│   ├── ChatBox.tsx (现有)
│   ├── MessageList.tsx (现有)
│   └── HistorySidebar.tsx (新增)
├── pages/
│   ├── ChatPage.tsx (修改)
│   └── HistoryPage.tsx (新增)
├── api/
│   └── qa.ts (扩展)
└── types.ts (扩展)
```

---

## 6. 测试计划

### 6.1 后端测试

- [ ] 数据库迁移成功
- [ ] 现有 API 功能不受影响
- [ ] 归档 API 正确更新状态
- [ ] 恢复 API 正确更新状态
- [ ] 删除 API 正确删除记录
- [ ] 按状态筛选正确工作
- [ ] 分页功能正确

### 6.2 前端测试

- [ ] 页面加载时正确恢复历史记录
- [ ] 侧边栏正确显示最近记录
- [ ] 点击侧边栏记录正确加载
- [ ] 独立历史页面正确显示记录列表
- [ ] 搜索功能正常工作
- [ ] 筛选功能正常工作
- [ ] 归档操作成功
- [ ] 删除确认对话框正常显示
- [ ] 删除操作成功
- [ ] 批量选择和批量删除正常

---

## 7. 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据库迁移失败 | 高 | 在测试环境先验证，备份数据 |
| 性能问题（大量记录） | 中 | 添加索引，分页加载 |
| 前端状态同步问题 | 低 | 使用 API 作为单一数据源 |
| 用户误删记录 | 中 | 确认对话框，未来可添加回收站 |

---

## 8. 未来扩展

- **回收站功能**：软删除，保留 30 天后自动彻底删除
- **用户系统集成**：按用户隔离数据
- **标签系统**：为记录添加自定义标签
- **导出功能**：支持导出为 Markdown、PDF 等格式
- **分享功能**：生成分享链接
- **高级搜索**：全文搜索、语义搜索

---

## 9. 附录

### 9.1 相关文件

- 后端模型：`backend/app/models/qa_record.py`
- 后端路由：`backend/app/api/routes/qa.py`
- 后端服务：`backend/app/services/qa_service.py`
- 前端页面：`frontend/src/pages/ChatPage.tsx`
- 前端组件：`frontend/src/components/MessageList.tsx`
- 前端类型：`frontend/src/types.ts`

### 9.2 参考资料

- SQLAlchemy 文档：https://docs.sqlalchemy.org/
- FastAPI 文档：https://fastapi.tiangolo.com/
- Ant Design 文档：https://ant.design/
- React Router 文档：https://reactrouter.com/

---

**文档作者：** Claude
**最后更新：** 2026-05-31
