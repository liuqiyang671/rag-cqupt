# 问题重写（Query Rewriting）实现计划

## 1. 概述

### 1.1 目标

实现问题重写功能，使用 LLM 将用户问题改写为更正式、更清晰的表述，提高检索准确率。

### 1.2 设计决策

- **重写策略**：Query Rewriting（使用 LLM 改写问题）
- **触发位置**：后端 RAG 服务（自动生效，无需前端改动）
- **查询数量**：2-3 个（原始查询 + 2 个重写查询）

### 1.3 预期效果

```
用户输入: "卡丢了咋整"
    ↓
重写查询:
  1. "卡丢了咋整" (原始)
  2. "校园卡丢失后如何处理" (重写)
  3. "校园卡挂失流程是什么" (重写)
    ↓
多查询检索 → 合并去重 → 重排序
    ↓
更准确的检索结果
```

---

## 2. 架构设计

### 2.1 新增文件

```
backend/app/services/
├── query_rewriting.py    # 新增：问题重写服务
└── rag_service.py        # 修改：集成问题重写
```

### 2.2 流程图

```
┌─────────────────────────────────────────────────────────────┐
│  RAGService.ask_stream()                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 1: 会话管理（现有）                                    │
│  • 获取或创建会话                                            │
│  • 加载最近 3 轮对话历史                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 2: 闲聊检测（现有）                                    │
│  • 检测是否为问候/感谢/告别/赞美                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 3: 问题重写（新增）                                    │
│  • 调用 QueryRewriter.rewrite_query()                        │
│  • 生成 2-3 个查询变体                                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 4: 多查询检索（新增）                                  │
│  • 对每个查询变体进行向量化                                   │
│  • 对每个查询变体进行混合检索                                 │
│  • 合并所有检索结果                                          │
│  • 去重并重排序                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 5: Prompt 构建（现有）                                 │
│  • 使用合并后的检索结果构建 Prompt                            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 6: LLM 生成 & 流式返回（现有）                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 详细设计

### 3.1 QueryRewriter 类

**文件**：`backend/app/services/query_rewriting.py`

```python
from __future__ import annotations

import logging
from typing import List

from app.services.llm.base import LLMClient

logger = logging.getLogger(__name__)

# 问题重写 Prompt
REWRITE_PROMPT = """你是一个查询优化专家。请将以下用户问题改写为 {count} 个不同的查询，以便更准确地检索校园知识库。

原始问题：{question}

要求：
1. 保持原始意图不变
2. 使用更正式、更清晰的表述
3. 覆盖不同的角度和可能的表述方式
4. 每个查询独立成行
5. 不要添加序号或额外说明

示例：
原始问题：卡丢了咋整
改写查询：
校园卡丢失后如何处理
校园卡挂失流程是什么
如何补办校园卡

请改写上述问题："""


class QueryRewriter:
    """问题重写器，使用 LLM 将用户问题改写为更清晰的查询"""

    def __init__(self, llm_client: LLMClient, max_queries: int = 3):
        self.llm_client = llm_client
        self.max_queries = max_queries

    async def rewrite_query(self, question: str) -> List[str]:
        """
        将用户问题改写为多个查询变体
        
        Args:
            question: 原始用户问题
            
        Returns:
            查询列表，包含原始查询和重写后的查询
        """
        # 如果问题很短或已经是正式表述，直接返回
        if len(question.strip()) <= 4:
            return [question]

        try:
            # 调用 LLM 进行问题重写
            prompt = REWRITE_PROMPT.format(
                question=question,
                count=self.max_queries - 1  # 减去原始查询
            )
            
            response = await self.llm_client.chat([
                {"role": "user", "content": prompt}
            ])
            
            # 解析重写结果
            rewritten_queries = self._parse_response(response)
            
            # 合并原始查询和重写查询
            all_queries = [question] + rewritten_queries[:self.max_queries - 1]
            
            # 去重
            unique_queries = list(dict.fromkeys(all_queries))
            
            logger.info(f"Query rewriting: '{question}' -> {unique_queries}")
            return unique_queries
            
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return [question]

    def _parse_response(self, response: str) -> List[str]:
        """解析 LLM 响应，提取重写后的查询"""
        queries = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # 跳过空行和序号
            if not line:
                continue
            # 移除序号（如 "1.", "2."）
            if line and line[0].isdigit() and len(line) > 2:
                line = line[2:].strip()
            if line:
                queries.append(line)
        return queries
```

### 3.2 MultiQueryRetriever 类

**文件**：`backend/app/services/query_rewriting.py`（追加）

```python
from sqlalchemy.orm import Session

from app.services.embedding.base import EmbeddingClient
from app.services.retrieval_service import (
    retrieve_hybrid_knowledge,
    RetrievalResult,
    build_retrieved_knowledge,
)


class MultiQueryRetriever:
    """多查询检索器，对多个查询进行检索并合并结果"""

    def __init__(
        self,
        db: Session,
        embedding_client: EmbeddingClient,
        top_k: int = 5,
    ):
        self.db = db
        self.embedding_client = embedding_client
        self.top_k = top_k

    async def retrieve(self, queries: List[str]) -> List[dict]:
        """
        对多个查询进行检索并合并结果
        
        Args:
            queries: 查询列表
            
        Returns:
            合并后的检索结果
        """
        all_results = []
        
        for query in queries:
            try:
                # 向量化
                embedding = await self.embedding_client.embed(query)
                
                # 混合检索
                results = retrieve_hybrid_knowledge(
                    db=self.db,
                    question=query,
                    query_embedding=embedding,
                    top_k=self.top_k,
                )
                
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Retrieval failed for query '{query}': {e}")
                continue
        
        # 去重并重排序
        return self._deduplicate_and_rerank(all_results)

    def _deduplicate_and_rerank(self, results: List[dict]) -> List[dict]:
        """去重并重排序检索结果"""
        # 按 ID 去重，保留最高分数
        seen = {}
        for result in results:
            result_id = result.get('id')
            if result_id is None:
                continue
            
            if result_id not in seen:
                seen[result_id] = result
            else:
                # 保留分数更高的结果
                if result.get('relevance_score', 0) > seen[result_id].get('relevance_score', 0):
                    seen[result_id] = result
        
        # 按分数排序
        sorted_results = sorted(
            seen.values(),
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        
        # 返回 top_k 个结果
        return sorted_results[:self.top_k]
```

### 3.3 修改 RAG 服务

**文件**：`backend/app/services/rag_service.py`

在 `RAGService` 类中集成问题重写功能：

```python
from app.services.query_rewriting import QueryRewriter, MultiQueryRetriever

class RAGService:
    def __init__(
        self,
        db: Session,
        embedding_client: EmbeddingClient,
        llm_client: LLMClient,
        model_provider: str,
        top_k: int,
        enable_query_rewriting: bool = True,  # 新增配置
    ):
        self.db = db
        self.embedding_client = embedding_client
        self.llm_client = llm_client
        self.model_provider = model_provider
        self.top_k = top_k
        self.enable_query_rewriting = enable_query_rewriting
        
        # 初始化问题重写器
        if enable_query_rewriting:
            self.query_rewriter = QueryRewriter(llm_client, max_queries=3)
            self.multi_query_retriever = MultiQueryRetriever(
                db=db,
                embedding_client=embedding_client,
                top_k=top_k,
            )

    async def ask_stream(self, question: str, session_id: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Stream the RAG answer as SSE events."""
        try:
            # ... 现有代码 ...

            # 1. Retrieve relevant knowledge
            if self.enable_query_rewriting:
                # 问题重写
                queries = await self.query_rewriter.rewrite_query(question)
                
                # 多查询检索
                context_items = await self.multi_query_retriever.retrieve(queries)
            else:
                # 原有逻辑
                query_embedding = await self.embedding_client.embed(question)
                context_items = retrieve_hybrid_knowledge(
                    self.db, question, query_embedding, self.top_k
                )

            # ... 后续代码 ...
```

### 3.4 配置选项

**文件**：`backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 问题重写配置
    enable_query_rewriting: bool = Field(default=True, alias="ENABLE_QUERY_REWRITING")
    query_rewriting_max_queries: int = Field(default=3, alias="QUERY_REWRITING_MAX_QUERIES")
```

---

## 4. 实现步骤

### 4.1 创建问题重写服务

**文件**：`backend/app/services/query_rewriting.py`

- [ ] 创建 `QueryRewriter` 类
- [ ] 实现 `rewrite_query` 方法
- [ ] 实现 `_parse_response` 方法
- [ ] 创建 `MultiQueryRetriever` 类
- [ ] 实现 `retrieve` 方法
- [ ] 实现 `_deduplicate_and_rerank` 方法

### 4.2 修改 RAG 服务

**文件**：`backend/app/services/rag_service.py`

- [ ] 导入 `QueryRewriter` 和 `MultiQueryRetriever`
- [ ] 修改 `__init__` 方法，添加 `enable_query_rewriting` 参数
- [ ] 修改 `ask_stream` 方法，集成问题重写逻辑
- [ ] 修改 `ask` 方法，集成问题重写逻辑

### 4.3 添加配置选项

**文件**：`backend/app/core/config.py`

- [ ] 添加 `enable_query_rewriting` 配置项
- [ ] 添加 `query_rewriting_max_queries` 配置项

### 4.4 编写测试

**文件**：`backend/tests/test_query_rewriting.py`

- [ ] 测试 `QueryRewriter.rewrite_query` 方法
- [ ] 测试 `MultiQueryRetriever.retrieve` 方法
- [ ] 测试去重和重排序逻辑
- [ ] 测试错误处理

### 4.5 更新文档

- [ ] 更新 README.md，添加问题重写功能说明
- [ ] 更新 API 文档，添加配置选项说明

---

## 5. 配置说明

### 5.1 环境变量

```bash
# 启用/禁用问题重写
ENABLE_QUERY_REWRITING=true

# 重写后的查询数量（包括原始查询）
QUERY_REWRITING_MAX_QUERIES=3
```

### 5.2 使用示例

```python
# 创建 RAG 服务（启用问题重写）
service = RAGService(
    db=db,
    embedding_client=embedding_client,
    llm_client=llm_client,
    model_provider=settings.model_provider,
    top_k=settings.top_k,
    enable_query_rewriting=True,  # 启用问题重写
)

# 流式问答
async for event in service.ask_stream("卡丢了咋整"):
    print(event)
```

---

## 6. 测试计划

### 6.1 单元测试

```python
# backend/tests/test_query_rewriting.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.query_rewriting import QueryRewriter, MultiQueryRetriever


@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.chat.return_value = "校园卡丢失后如何处理\n校园卡挂失流程是什么\n如何补办校园卡"
    return client


@pytest.fixture
def mock_embedding_client():
    client = AsyncMock()
    client.embed.return_value = [0.1] * 4096
    return client


@pytest.mark.asyncio
async def test_rewrite_query(mock_llm_client):
    rewriter = QueryRewriter(mock_llm_client, max_queries=3)
    queries = await rewriter.rewrite_query("卡丢了咋整")
    
    assert len(queries) == 3
    assert queries[0] == "卡丢了咋整"  # 原始查询
    assert "校园卡丢失后如何处理" in queries
    assert "校园卡挂失流程是什么" in queries


@pytest.mark.asyncio
async def test_rewrite_query_short_input(mock_llm_client):
    rewriter = QueryRewriter(mock_llm_client, max_queries=3)
    queries = await rewriter.rewrite_query("你好")
    
    assert len(queries) == 1
    assert queries[0] == "你好"


@pytest.mark.asyncio
async def test_multi_query_retriever(mock_embedding_client):
    db = MagicMock()
    retriever = MultiQueryRetriever(db, mock_embedding_client, top_k=5)
    
    # 模拟检索结果
    with pytest.raises(Exception):
        # 由于 db 是 mock，实际检索会失败
        await retriever.retrieve(["查询1", "查询2"])
```

### 6.2 集成测试

```python
# 测试完整流程
@pytest.mark.asyncio
async def test_rag_with_query_rewriting():
    # 创建真实的 RAG 服务
    service = RAGService(
        db=db,
        embedding_client=embedding_client,
        llm_client=llm_client,
        model_provider="local",
        top_k=5,
        enable_query_rewriting=True,
    )
    
    # 测试问答
    result = await service.ask("卡丢了咋整")
    
    assert result["answer"]
    assert result["retrieved_context"]
    assert len(result["retrieved_context"]) > 0
```

---

## 7. 预期效果

### 7.1 测试用例

| 原始查询 | 重写查询 | 预期效果 |
|---------|---------|---------|
| "卡丢了咋整" | "校园卡丢失后如何处理", "校园卡挂失流程是什么" | 提高检索准确率 |
| "怎么弄那个" | "如何办理校园卡挂失", "校园卡补办流程" | 澄清用户意图 |
| "学校有什么福利" | "奖学金政策", "助学金申请条件", "勤工助学机会" | 扩展检索范围 |
| "图书馆怎么借书" | "图书馆借阅流程", "图书借阅规则" | 提高检索准确率 |

### 7.2 性能影响

- **延迟增加**：约 1-2 秒（LLM 调用时间）
- **成本增加**：每次问答多 1 次 LLM 调用
- **检索质量**：预期提升 20-30%

---

## 8. 风险和缓解措施

### 8.1 风险

1. **LLM 调用失败**：问题重写失败会影响整个问答流程
2. **重写质量差**：LLM 可能生成不相关的查询
3. **延迟增加**：问题重写会增加响应时间

### 8.2 缓解措施

1. **降级策略**：问题重写失败时，使用原始查询
2. **质量监控**：记录重写结果，定期评估质量
3. **性能优化**：支持异步并行检索，减少延迟

---

## 9. 后续优化

### 9.1 短期优化

- 添加重写质量评估指标
- 优化 Prompt 提高重写质量
- 支持异步并行检索

### 9.2 长期优化

- 实现 HyDE（假设性文档嵌入）
- 实现 Query Decomposition（复杂问题分解）
- 实现自适应重写策略

---

## 10. 总结

本方案实现了问题重写功能，通过 LLM 将用户问题改写为更清晰的查询，提高检索准确率。方案设计考虑了：

- **可配置性**：通过环境变量控制是否启用
- **容错性**：问题重写失败时降级到原有逻辑
- **可扩展性**：支持后续添加更多重写策略

预期效果：检索准确率提升 20-30%，用户体验显著改善。
