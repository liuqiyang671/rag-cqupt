from typing import List

import httpx

from app.core.ai_errors import EmbeddingProviderError
from app.services.embedding.base import EmbeddingClient


class SiliconFlowEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str, base_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension

    async def embed(self, text: str) -> List[float]:
        if not self.api_key:
            raise EmbeddingProviderError("硅基流动 Embedding 不可用：未配置 SILICONFLOW_API_KEY。")

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
                values = [float(value) for value in embedding]
                if len(values) != self.dimension:
                    raise EmbeddingProviderError(
                        f"需要重新构建知识库向量：硅基流动 Embedding 模型 {self.model} 返回 {len(values)} 维，"
                        f"当前配置需要 {self.dimension} 维。"
                    )
                return values
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"硅基流动 Embedding 不可用：{self.model}。") from exc
