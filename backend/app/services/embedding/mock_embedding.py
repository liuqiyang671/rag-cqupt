import hashlib
import math
import re
from typing import List

from app.services.embedding.base import EmbeddingClient


TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")


class MockEmbeddingClient(EmbeddingClient):
    """Deterministic lexical hashing embedding for local MVP and tests."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    async def embed(self, text: str) -> List[float]:
        return self.embed_sync(text)

    def embed_sync(self, text: str) -> List[float]:
        vector = [0.0 for _ in range(self.dimension)]
        tokens = TOKEN_RE.findall(text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 8) for value in vector]

