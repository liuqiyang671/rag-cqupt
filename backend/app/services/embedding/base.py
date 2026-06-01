from abc import ABC, abstractmethod
from typing import List


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Return a numeric embedding for the given text."""

