import httpx

from app.services.embedding.base import EmbeddingClient
from app.services.embedding.mock_embedding import MockEmbeddingClient


class SiliconFlowEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str, base_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = MockEmbeddingClient(dimension=dimension)

    async def embed(self, text: str) -> list[float]:
        if not self.api_key:
            return await self.fallback.embed(text)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                payload = response.json()
                embedding = payload["data"][0]["embedding"]
                return [float(value) for value in embedding]
        except Exception:
            return await self.fallback.embed(text)

