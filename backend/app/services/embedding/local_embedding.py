import httpx

from app.services.embedding.base import EmbeddingClient
from app.services.embedding.mock_embedding import MockEmbeddingClient


class LocalEmbeddingClient(EmbeddingClient):
    def __init__(self, base_url: str, model: str, dimension: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = MockEmbeddingClient(dimension=dimension)

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                payload = response.json()
                embedding = payload.get("embedding")
                if isinstance(embedding, list) and embedding:
                    return [float(value) for value in embedding]
        except Exception:
            pass
        return await self.fallback.embed(text)
