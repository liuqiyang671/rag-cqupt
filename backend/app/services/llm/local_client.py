import json
from typing import AsyncGenerator, Dict, List

import httpx

from app.core.ai_errors import ModelProviderError
from app.services.llm.base import LLMClient


class LocalLLMClient(LLMClient):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "think": False,
                        "options": {"num_predict": 384},
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("message", {}).get("content") or payload.get("response")
                if content:
                    return str(content)
                raise ModelProviderError(f"本地问答模型不可用：{self.model} 未返回回答内容。")
        except ModelProviderError:
            raise
        except Exception as exc:
            raise ModelProviderError(f"本地问答模型不可用：{self.model}。请确认 Ollama 已启动且模型已安装。") from exc

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "think": False,
                        "options": {"num_predict": 384},
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            return
        except ModelProviderError:
            raise
        except Exception as exc:
            raise ModelProviderError(f"本地问答模型不可用：{self.model}。请确认 Ollama 已启动且模型已安装。") from exc
