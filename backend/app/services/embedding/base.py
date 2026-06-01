from abc import ABC, abstractmethod


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return a numeric embedding for the given text."""

