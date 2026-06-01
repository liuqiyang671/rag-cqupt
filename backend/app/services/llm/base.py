from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List


class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Return a chat completion for the supplied messages."""

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Yield incremental answer chunks. Default: delegate to chat() and yield once."""
        yield await self.chat(messages)

