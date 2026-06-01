from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Return a chat completion for the supplied messages."""

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        """Yield incremental answer chunks. Default: delegate to chat() and yield once."""
        yield await self.chat(messages)

