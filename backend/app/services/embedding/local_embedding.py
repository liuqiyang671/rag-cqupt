from typing import List

import httpx

from app.core.ai_errors import EmbeddingProviderError
from app.services.embedding.base import EmbeddingClient


class LocalEmbeddingClient(EmbeddingClient):
    def __init__(self, base_url: str, model: str, dimension: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension

    async def embed(self, text: str) -> List[float]:
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
                    values = [float(value) for value in embedding]
                    if len(values) != self.dimension:
                        raise EmbeddingProviderError(
                            f"需要重新构建知识库向量：本地 Embedding 模型 {self.model} 返回 {len(values)} 维，"
                            f"当前配置需要 {self.dimension} 维。请确认 EMBEDDING_DIMENSION 后执行 "
                            "py -3.13 -m app.scripts.rebuild_knowledge_embeddings。"
                        )
                    return values
                raise EmbeddingProviderError(f"本地 Embedding 模型不可用：{self.model} 未返回 embedding。")
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(
                f"本地 Embedding 模型不可用：{self.model}。请确认 Ollama 已启动且模型已安装。"
            ) from exc
