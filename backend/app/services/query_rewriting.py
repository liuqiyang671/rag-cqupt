"""问题重写服务

使用 LLM 将用户问题改写为更清晰的查询，提高检索准确率。
"""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

from app.services.embedding.base import EmbeddingClient
from app.services.llm.base import LLMClient
from app.services.retrieval_service import retrieve_hybrid_knowledge

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
        """
        初始化问题重写器

        Args:
            llm_client: LLM 客户端
            max_queries: 最大查询数量（包括原始查询）
        """
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
        """
        解析 LLM 响应，提取重写后的查询

        Args:
            response: LLM 响应文本

        Returns:
            重写后的查询列表
        """
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


class MultiQueryRetriever:
    """多查询检索器，对多个查询进行检索并合并结果"""

    def __init__(
        self,
        db: Session,
        embedding_client: EmbeddingClient,
        top_k: int = 5,
    ):
        """
        初始化多查询检索器

        Args:
            db: 数据库会话
            embedding_client: Embedding 客户端
            top_k: 返回结果数量
        """
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
        """
        去重并重排序检索结果

        Args:
            results: 原始检索结果

        Returns:
            去重并重排序后的结果
        """
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
