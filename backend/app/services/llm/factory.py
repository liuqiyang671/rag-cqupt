from app.core.config import Settings
from app.services.llm.base import LLMClient
from app.services.llm.fallback_client import FallbackLLMClient
from app.services.llm.fault_tolerant_client import FaultTolerantLLMClient
from app.services.llm.local_client import LocalLLMClient
from app.services.llm.siliconflow_client import SiliconFlowLLMClient


def get_llm_client(settings: Settings) -> LLMClient:
    """
    获取 LLM 客户端，支持自动故障转移

    根据配置返回容错客户端：
    - 如果配置了多个模型，自动创建故障转移链
    - 如果只配置了一个模型，使用该模型
    - 如果配置为 mock，使用回退客户端

    故障转移优先级：
    1. 主模型（根据 MODEL_PROVIDER 配置）
    2. 备用模型（如果配置了其他模型）
    3. FallbackLLMClient（基于规则的回退）
    """
    provider = settings.model_provider.lower()

    # 创建主模型客户端
    primary_client: LLMClient
    if provider == "siliconflow":
        primary_client = SiliconFlowLLMClient(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_chat_model,
        )
    elif provider == "mock":
        return FallbackLLMClient()
    else:
        primary_client = LocalLLMClient(
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model,
        )

    # 创建备用模型客户端列表
    fallback_clients: list[LLMClient] = []

    # 如果主模型不是 SiliconFlow，添加为备用
    if provider != "siliconflow" and settings.siliconflow_api_key:
        fallback_clients.append(
            SiliconFlowLLMClient(
                api_key=settings.siliconflow_api_key,
                base_url=settings.siliconflow_base_url,
                model=settings.siliconflow_chat_model,
            )
        )

    # 如果主模型不是 Local，添加为备用
    if provider != "local":
        fallback_clients.append(
            LocalLLMClient(
                base_url=settings.local_llm_base_url,
                model=settings.local_llm_model,
            )
        )

    # 始终添加 FallbackLLMClient 作为最后的回退
    fallback_clients.append(FallbackLLMClient())

    # 如果只有一个客户端，直接返回
    if not fallback_clients:
        return primary_client

    # 返回容错客户端
    return FaultTolerantLLMClient(
        primary_client=primary_client,
        fallback_clients=fallback_clients,
    )
