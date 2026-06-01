import json
from typing import AsyncGenerator

import httpx

from app.services.llm.base import LLMClient
from app.services.llm.fallback_client import FallbackLLMClient


class SiliconFlowLLMClient(LLMClient):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = FallbackLLMClient()

    async def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            return await self.fallback.chat(messages)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages, "temperature": 0.2},
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                return str(content)
        except Exception:
            return await self.fallback.chat(messages)

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield await self.fallback.chat(messages)
            return

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages, "temperature": 0.2, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            return
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
        except Exception:
            yield await self.fallback.chat(messages)

