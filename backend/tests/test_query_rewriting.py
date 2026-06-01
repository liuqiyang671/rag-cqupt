"""问题重写服务测试"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.query_rewriting import QueryRewriter, QueryDecomposer, MultiQueryRetriever


@pytest.fixture
def mock_llm_client():
    """模拟 LLM 客户端"""
    client = AsyncMock()
    client.chat.return_value = "校园卡丢失后如何处理\n校园卡挂失流程是什么\n如何补办校园卡"
    return client


@pytest.fixture
def mock_embedding_client():
    """模拟 Embedding 客户端"""
    client = AsyncMock()
    client.embed.return_value = [0.1] * 4096
    return client


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return MagicMock()


class TestQueryRewriter:
    """测试 QueryRewriter 类"""

    @pytest.mark.asyncio
    async def test_rewrite_query_normal(self, mock_llm_client):
        """测试正常问题重写"""
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        queries = await rewriter.rewrite_query("卡丢了咋整")

        assert len(queries) == 3
        assert queries[0] == "卡丢了咋整"  # 原始查询
        assert "校园卡丢失后如何处理" in queries
        assert "校园卡挂失流程是什么" in queries

    @pytest.mark.asyncio
    async def test_rewrite_query_short_input(self, mock_llm_client):
        """测试短输入不进行重写"""
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        queries = await rewriter.rewrite_query("你好")

        assert len(queries) == 1
        assert queries[0] == "你好"

    @pytest.mark.asyncio
    async def test_rewrite_query_llm_failure(self, mock_llm_client):
        """测试 LLM 调用失败时的降级处理"""
        mock_llm_client.chat.side_effect = Exception("LLM service unavailable")
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        queries = await rewriter.rewrite_query("卡丢了咋整")

        # 失败时应该返回原始查询
        assert len(queries) == 1
        assert queries[0] == "卡丢了咋整"

    @pytest.mark.asyncio
    async def test_rewrite_query_deduplication(self, mock_llm_client):
        """测试查询去重"""
        # 模拟 LLM 返回重复的查询
        mock_llm_client.chat.return_value = "卡丢了咋整\n校园卡丢失后如何处理\n卡丢了咋整"
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        queries = await rewriter.rewrite_query("卡丢了咋整")

        # 应该去重
        assert len(queries) == 2
        assert queries[0] == "卡丢了咋整"
        assert "校园卡丢失后如何处理" in queries

    def test_parse_response_with_numbers(self, mock_llm_client):
        """测试解析带序号的响应"""
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        response = "1. 校园卡丢失后如何处理\n2. 校园卡挂失流程是什么\n3. 如何补办校园卡"
        queries = rewriter._parse_response(response)

        assert len(queries) == 3
        assert "校园卡丢失后如何处理" in queries
        assert "校园卡挂失流程是什么" in queries
        assert "如何补办校园卡" in queries

    def test_parse_response_without_numbers(self, mock_llm_client):
        """测试解析不带序号的响应"""
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        response = "校园卡丢失后如何处理\n校园卡挂失流程是什么\n如何补办校园卡"
        queries = rewriter._parse_response(response)

        assert len(queries) == 3

    def test_parse_response_empty_lines(self, mock_llm_client):
        """测试解析包含空行的响应"""
        rewriter = QueryRewriter(mock_llm_client, max_queries=3)
        response = "校园卡丢失后如何处理\n\n校园卡挂失流程是什么\n\n"
        queries = rewriter._parse_response(response)

        assert len(queries) == 2


class TestMultiQueryRetriever:
    """测试 MultiQueryRetriever 类"""

    @pytest.mark.asyncio
    async def test_retrieve_single_query(self, mock_db, mock_embedding_client):
        """测试单查询检索"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=5)

        # 模拟检索结果
        mock_results = [
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.9},
            {"id": 2, "title": "校园卡补办", "relevance_score": 0.8},
        ]

        with patch("app.services.query_rewriting.retrieve_hybrid_knowledge", return_value=mock_results):
            results = await retriever.retrieve(["校园卡丢了怎么办"])

            assert len(results) == 2
            assert results[0]["id"] == 1
            assert results[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_retrieve_multi_queries(self, mock_db, mock_embedding_client):
        """测试多查询检索和合并"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=5)

        # 模拟不同查询的检索结果
        mock_results_1 = [
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.9},
            {"id": 2, "title": "校园卡补办", "relevance_score": 0.8},
        ]
        mock_results_2 = [
            {"id": 2, "title": "校园卡补办", "relevance_score": 0.85},  # 重复，分数不同
            {"id": 3, "title": "一卡通服务", "relevance_score": 0.7},
        ]

        with patch("app.services.query_rewriting.retrieve_hybrid_knowledge", side_effect=[mock_results_1, mock_results_2]):
            results = await retriever.retrieve(["校园卡丢了怎么办", "如何补办校园卡"])

            # 应该去重并保留最高分数
            assert len(results) == 3
            assert results[0]["id"] == 1  # 最高分
            assert results[1]["id"] == 2  # 保留最高分数 0.85
            assert results[2]["id"] == 3

    @pytest.mark.asyncio
    async def test_retrieve_with_failure(self, mock_db, mock_embedding_client):
        """测试检索失败时的容错处理"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=5)

        # 模拟第一个查询失败，第二个成功
        mock_results = [
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.9},
        ]

        with patch("app.services.query_rewriting.retrieve_hybrid_knowledge", side_effect=[Exception("DB error"), mock_results]):
            results = await retriever.retrieve(["查询1", "查询2"])

            # 应该只返回成功的结果
            assert len(results) == 1
            assert results[0]["id"] == 1

    def test_deduplicate_and_rerank(self, mock_db, mock_embedding_client):
        """测试去重和重排序"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=5)

        # 模拟重复的结果
        results = [
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.9},
            {"id": 2, "title": "校园卡补办", "relevance_score": 0.8},
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.85},  # 重复，分数较低
            {"id": 3, "title": "一卡通服务", "relevance_score": 0.7},
        ]

        deduplicated = retriever._deduplicate_and_rerank(results)

        # 应该去重并按分数排序
        assert len(deduplicated) == 3
        assert deduplicated[0]["id"] == 1  # 保留最高分数 0.9
        assert deduplicated[0]["relevance_score"] == 0.9
        assert deduplicated[1]["id"] == 2
        assert deduplicated[2]["id"] == 3

    def test_deduplicate_top_k(self, mock_db, mock_embedding_client):
        """测试 top_k 限制"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=2)

        results = [
            {"id": 1, "title": "校园卡挂失", "relevance_score": 0.9},
            {"id": 2, "title": "校园卡补办", "relevance_score": 0.8},
            {"id": 3, "title": "一卡通服务", "relevance_score": 0.7},
        ]

        deduplicated = retriever._deduplicate_and_rerank(results)

        # 应该只返回 top_k 个结果
        assert len(deduplicated) == 2
        assert deduplicated[0]["id"] == 1
        assert deduplicated[1]["id"] == 2

    def test_deduplicate_empty_results(self, mock_db, mock_embedding_client):
        """测试空结果"""
        retriever = MultiQueryRetriever(mock_db, mock_embedding_client, top_k=5)

        deduplicated = retriever._deduplicate_and_rerank([])

        assert len(deduplicated) == 0


class TestQueryDecomposer:
    """测试 QueryDecomposer 类"""

    @pytest.fixture
    def decomposer(self, mock_llm_client):
        """创建问题拆分器实例"""
        return QueryDecomposer(mock_llm_client, max_sub_queries=5)

    @pytest.mark.asyncio
    async def test_decompose_multiple_questions(self, decomposer, mock_llm_client):
        """测试拆分多个问题"""
        mock_llm_client.chat.return_value = "校园卡怎么挂失\n图书馆开放时间是什么\n宿舍怎么报修"
        queries = await decomposer.decompose_query("校园卡怎么挂失？图书馆开放时间是什么？宿舍怎么报修？")

        assert len(queries) == 3
        assert "校园卡怎么挂失" in queries
        assert "图书馆开放时间是什么" in queries
        assert "宿舍怎么报修" in queries

    @pytest.mark.asyncio
    async def test_decompose_single_question(self, decomposer, mock_llm_client):
        """测试单个问题不拆分"""
        mock_llm_client.chat.return_value = "校园卡丢了怎么办"
        queries = await decomposer.decompose_query("校园卡丢了怎么办")

        assert len(queries) == 1
        assert queries[0] == "校园卡丢了怎么办"

    @pytest.mark.asyncio
    async def test_decompose_short_input(self, decomposer, mock_llm_client):
        """测试短输入不拆分"""
        queries = await decomposer.decompose_query("你好")

        assert len(queries) == 1
        assert queries[0] == "你好"

    @pytest.mark.asyncio
    async def test_decompose_llm_failure(self, decomposer, mock_llm_client):
        """测试 LLM 调用失败时的降级处理"""
        mock_llm_client.chat.side_effect = Exception("LLM service unavailable")
        queries = await decomposer.decompose_query("校园卡怎么挂失？图书馆开放时间是什么？")

        # 失败时应该返回原始查询
        assert len(queries) == 1
        assert queries[0] == "校园卡怎么挂失？图书馆开放时间是什么？"

    @pytest.mark.asyncio
    async def test_decompose_max_sub_queries(self, decomposer, mock_llm_client):
        """测试子问题数量限制"""
        mock_llm_client.chat.return_value = "问题1\n问题2\n问题3\n问题4\n问题5\n问题6\n问题7"
        queries = await decomposer.decompose_query("问题1？问题2？问题3？问题4？问题5？问题6？问题7？")

        # 应该限制为 max_sub_queries=5
        assert len(queries) == 5

    def test_parse_response_with_numbers(self, decomposer):
        """测试解析带序号的响应"""
        response = "1. 校园卡怎么挂失\n2. 图书馆开放时间是什么\n3. 宿舍怎么报修"
        queries = decomposer._parse_response(response)

        assert len(queries) == 3
        assert "校园卡怎么挂失" in queries
        assert "图书馆开放时间是什么" in queries
        assert "宿舍怎么报修" in queries

    def test_parse_response_without_numbers(self, decomposer):
        """测试解析不带序号的响应"""
        response = "校园卡怎么挂失\n图书馆开放时间是什么\n宿舍怎么报修"
        queries = decomposer._parse_response(response)

        assert len(queries) == 3

    def test_parse_response_empty_lines(self, decomposer):
        """测试解析包含空行的响应"""
        response = "校园卡怎么挂失\n\n图书馆开放时间是什么\n\n"
        queries = decomposer._parse_response(response)

        assert len(queries) == 2
