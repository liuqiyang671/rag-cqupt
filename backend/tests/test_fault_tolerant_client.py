"""容错 LLM 客户端测试"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Dict, List

from app.core.ai_errors import ModelProviderError
from app.services.llm.base import LLMClient
from app.services.llm.fault_tolerant_client import FaultTolerantLLMClient, ModelHealth


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端"""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        self.call_count += 1
        if self.should_fail:
            raise ModelProviderError(f"{self.name} failed")
        return f"Response from {self.name}"

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        self.call_count += 1
        if self.should_fail:
            raise ModelProviderError(f"{self.name} failed")
        yield f"Chunk from {self.name}"


@pytest.fixture
def primary_client():
    return MockLLMClient("primary")


@pytest.fixture
def fallback_client():
    return MockLLMClient("fallback")


@pytest.fixture
def failing_client():
    return MockLLMClient("failing", should_fail=True)


class TestModelHealth:
    """测试 ModelHealth 类"""

    def test_initial_state(self):
        """测试初始状态"""
        health = ModelHealth("test")
        assert health.is_healthy is True
        assert health.failure_count == 0
        assert health.success_count == 0
        assert health.last_failure_time is None

    def test_record_success(self):
        """测试记录成功"""
        health = ModelHealth("test")
        health.record_success()
        assert health.is_healthy is True
        assert health.success_count == 1

    def test_record_failure(self):
        """测试记录失败"""
        health = ModelHealth("test")
        health.record_failure()
        assert health.failure_count == 1
        assert health.last_failure_time is not None

    def test_unhealthy_after_consecutive_failures(self):
        """测试连续失败后标记为不健康"""
        health = ModelHealth("test")
        for _ in range(3):
            health.record_failure()
        assert health.is_healthy is False

    def test_should_retry_when_healthy(self):
        """测试健康状态下应该重试"""
        health = ModelHealth("test")
        assert health.should_retry() is True

    def test_should_not_retry_when_unhealthy(self):
        """测试不健康状态下不应该重试"""
        health = ModelHealth("test")
        for _ in range(3):
            health.record_failure()
        assert health.should_retry() is False


class TestFaultTolerantLLMClient:
    """测试 FaultTolerantLLMClient 类"""

    @pytest.mark.asyncio
    async def test_primary_success(self, primary_client, fallback_client):
        """测试主模型成功"""
        client = FaultTolerantLLMClient(
            primary_client=primary_client,
            fallback_clients=[fallback_client],
        )
        result = await client.chat([{"role": "user", "content": "test"}])
        assert result == "Response from primary"
        assert primary_client.call_count == 1
        assert fallback_client.call_count == 0

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, failing_client, fallback_client):
        """测试主模型失败时切换到备用模型"""
        client = FaultTolerantLLMClient(
            primary_client=failing_client,
            fallback_clients=[fallback_client],
        )
        result = await client.chat([{"role": "user", "content": "test"}])
        assert result == "Response from fallback"
        assert failing_client.call_count == 1
        assert fallback_client.call_count == 1

    @pytest.mark.asyncio
    async def test_all_models_fail(self, failing_client):
        """测试所有模型都失败"""
        client = FaultTolerantLLMClient(
            primary_client=failing_client,
            fallback_clients=[failing_client],
        )
        with pytest.raises(ModelProviderError, match="All LLM models failed"):
            await client.chat([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_stream_primary_success(self, primary_client, fallback_client):
        """测试流式调用主模型成功"""
        client = FaultTolerantLLMClient(
            primary_client=primary_client,
            fallback_clients=[fallback_client],
        )
        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0] == "Chunk from primary"

    @pytest.mark.asyncio
    async def test_stream_fallback_on_failure(self, failing_client, fallback_client):
        """测试流式调用失败时切换到备用模型"""
        client = FaultTolerantLLMClient(
            primary_client=failing_client,
            fallback_clients=[fallback_client],
        )
        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0] == "Chunk from fallback"

    @pytest.mark.asyncio
    async def test_health_status(self, primary_client, failing_client):
        """测试健康状态查询"""
        client = FaultTolerantLLMClient(
            primary_client=primary_client,
            fallback_clients=[failing_client],
        )

        # 调用一次成功
        await client.chat([{"role": "user", "content": "test"}])

        # 调用一次失败
        try:
            failing_client.should_fail = True
            await client.chat([{"role": "user", "content": "test"}])
        except ModelProviderError:
            pass

        status = client.get_health_status()
        assert "primary:MockLLMClient" in status
        assert "fallback:MockLLMClient" in status

    @pytest.mark.asyncio
    async def test_reset_health(self, primary_client, failing_client):
        """测试重置健康状态"""
        client = FaultTolerantLLMClient(
            primary_client=primary_client,
            fallback_clients=[failing_client],
        )

        # 使主模型失败
        primary_client.should_fail = True
        for _ in range(3):
            try:
                await client.chat([{"role": "user", "content": "test"}])
            except ModelProviderError:
                pass

        # 验证主模型不健康
        status = client.get_health_status()
        assert status["primary:MockLLMClient"]["is_healthy"] is False

        # 重置健康状态
        client.reset_health("primary:MockLLMClient")
        status = client.get_health_status()
        assert status["primary:MockLLMClient"]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_multiple_fallbacks(self, failing_client, fallback_client):
        """测试多个备用模型"""
        another_fallback = MockLLMClient("another_fallback")
        client = FaultTolerantLLMClient(
            primary_client=failing_client,
            fallback_clients=[failing_client, fallback_client, another_fallback],
        )
        result = await client.chat([{"role": "user", "content": "test"}])
        # 应该跳过失败的主模型和第一个失败的备用模型，使用第二个备用模型
        assert result == "Response from fallback"
