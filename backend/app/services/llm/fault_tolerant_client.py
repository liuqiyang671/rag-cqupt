"""容错 LLM 客户端

支持自动故障转移，当主模型失败时自动切换到备用模型。
"""

from __future__ import annotations

import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

from app.core.ai_errors import ModelProviderError
from app.services.llm.base import LLMClient

logger = logging.getLogger(__name__)

# 模型健康状态缓存时间（秒）
HEALTH_CACHE_TTL = 300  # 5 分钟


class ModelHealth:
    """模型健康状态追踪"""

    def __init__(self, name: str):
        self.name = name
        self.is_healthy = True
        self.last_failure_time: Optional[float] = None
        self.failure_count = 0
        self.success_count = 0

    def record_success(self):
        """记录成功调用"""
        self.is_healthy = True
        self.failure_count = 0
        self.success_count += 1

    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        # 连续失败 3 次标记为不健康
        if self.failure_count >= 3:
            self.is_healthy = False
            logger.warning(f"Model {self.name} marked as unhealthy after {self.failure_count} consecutive failures")

    def should_retry(self) -> bool:
        """判断是否应该重试"""
        if self.is_healthy:
            return True
        # 如果距离上次失败超过缓存时间，重新尝试
        if self.last_failure_time and (time.time() - self.last_failure_time) > HEALTH_CACHE_TTL:
            logger.info(f"Model {self.name} health cache expired, retrying")
            self.is_healthy = True
            self.failure_count = 0
            return True
        return False


class FaultTolerantLLMClient(LLMClient):
    """容错 LLM 客户端，支持自动故障转移

    使用示例：
    ```python
    client = FaultTolerantLLMClient(
        primary_client=local_client,
        fallback_clients=[siliconflow_client, fallback_client],
    )
    ```
    """

    def __init__(
        self,
        primary_client: LLMClient,
        fallback_clients: Optional[List[LLMClient]] = None,
    ):
        """
        初始化容错客户端

        Args:
            primary_client: 主模型客户端
            fallback_clients: 备用模型客户端列表（按优先级排序）
        """
        self.primary_client = primary_client
        self.fallback_clients = fallback_clients or []

        # 为所有客户端创建健康状态追踪
        all_clients = [primary_client] + self.fallback_clients
        self.health_map: Dict[int, ModelHealth] = {}
        for i, client in enumerate(all_clients):
            name = self._get_client_name(client, i == 0)
            self.health_map[id(client)] = ModelHealth(name)

    def _get_client_name(self, client: LLMClient, is_primary: bool) -> str:
        """获取客户端名称"""
        prefix = "primary" if is_primary else "fallback"
        class_name = client.__class__.__name__
        return f"{prefix}:{class_name}"

    def _get_all_clients(self) -> List[LLMClient]:
        """获取所有客户端（按优先级排序）"""
        return [self.primary_client] + self.fallback_clients

    def _get_healthy_clients(self) -> List[LLMClient]:
        """获取所有健康的客户端（按优先级排序）"""
        clients = []
        for client in self._get_all_clients():
            health = self.health_map.get(id(client))
            if health and health.should_retry():
                clients.append(client)
        return clients

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        调用 LLM 进行对话，支持自动故障转移

        Args:
            messages: 对话消息列表

        Returns:
            LLM 回答内容

        Raises:
            ModelProviderError: 所有模型都失败时抛出
        """
        last_error = None
        healthy_clients = self._get_healthy_clients()

        if not healthy_clients:
            # 如果所有模型都不健康，强制尝试主模型
            healthy_clients = [self.primary_client]
            logger.warning("All models unhealthy, forcing primary model attempt")

        for client in healthy_clients:
            health = self.health_map.get(id(client))
            client_name = health.name if health else client.__class__.__name__

            try:
                logger.info(f"Attempting to use model: {client_name}")
                result = await client.chat(messages)

                # 记录成功
                if health:
                    health.record_success()
                logger.info(f"Model {client_name} succeeded")
                return result

            except Exception as e:
                # 记录失败
                if health:
                    health.record_failure()
                logger.warning(f"Model {client_name} failed: {e}")
                last_error = e
                continue

        # 所有模型都失败
        error_msg = f"All LLM models failed. Last error: {last_error}"
        logger.error(error_msg)
        raise ModelProviderError(error_msg)

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        调用 LLM 进行流式对话，支持自动故障转移

        Args:
            messages: 对话消息列表

        Yields:
            LLM 回答的文本片段

        Raises:
            ModelProviderError: 所有模型都失败时抛出
        """
        last_error = None
        healthy_clients = self._get_healthy_clients()

        if not healthy_clients:
            healthy_clients = [self.primary_client]
            logger.warning("All models unhealthy, forcing primary model attempt")

        for client in healthy_clients:
            health = self.health_map.get(id(client))
            client_name = health.name if health else client.__class__.__name__

            try:
                logger.info(f"Attempting to use model (stream): {client_name}")

                # 收集所有输出，如果中途失败需要回退
                chunks = []
                async for chunk in client.chat_stream(messages):
                    chunks.append(chunk)
                    yield chunk

                # 记录成功
                if health:
                    health.record_success()
                logger.info(f"Model {client_name} stream succeeded")
                return

            except Exception as e:
                # 记录失败
                if health:
                    health.record_failure()
                logger.warning(f"Model {client_name} stream failed: {e}")
                last_error = e

                # 如果已经开始输出，无法回退到其他模型
                if chunks:
                    logger.warning(f"Partial output received from {client_name}, cannot fallback")
                    return

                continue

        # 所有模型都失败
        error_msg = f"All LLM models failed. Last error: {last_error}"
        logger.error(error_msg)
        raise ModelProviderError(error_msg)

    def get_health_status(self) -> Dict[str, Dict]:
        """获取所有模型的健康状态"""
        status = {}
        for client in self._get_all_clients():
            health = self.health_map.get(id(client))
            if health:
                status[health.name] = {
                    "is_healthy": health.is_healthy,
                    "failure_count": health.failure_count,
                    "success_count": health.success_count,
                    "last_failure_time": health.last_failure_time,
                }
        return status

    def reset_health(self, client_name: Optional[str] = None):
        """
        重置模型健康状态

        Args:
            client_name: 要重置的模型名称，如果为 None 则重置所有
        """
        for health in self.health_map.values():
            if client_name is None or health.name == client_name:
                health.is_healthy = True
                health.failure_count = 0
                health.last_failure_time = None
                logger.info(f"Reset health for model: {health.name}")
