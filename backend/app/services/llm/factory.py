from app.core.config import Settings
from app.services.llm.base import LLMClient
from app.services.llm.fallback_client import FallbackLLMClient
from app.services.llm.local_client import LocalLLMClient
from app.services.llm.siliconflow_client import SiliconFlowLLMClient


def get_llm_client(settings: Settings) -> LLMClient:
    provider = settings.model_provider.lower()
    if provider == "siliconflow":
        return SiliconFlowLLMClient(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_chat_model,
        )
    if provider == "mock":
        return FallbackLLMClient()
    return LocalLLMClient(base_url=settings.local_llm_base_url, model=settings.local_llm_model)
