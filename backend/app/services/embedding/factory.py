from app.core.config import Settings
from app.services.embedding.base import EmbeddingClient
from app.services.embedding.local_embedding import LocalEmbeddingClient
from app.services.embedding.mock_embedding import MockEmbeddingClient
from app.services.embedding.siliconflow_embedding import SiliconFlowEmbeddingClient


def get_embedding_client(settings: Settings) -> EmbeddingClient:
    provider = settings.embedding_provider.lower()
    if provider == "siliconflow":
        return SiliconFlowEmbeddingClient(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_embedding_model,
            dimension=settings.embedding_dimension,
        )
    if provider == "mock":
        return MockEmbeddingClient(dimension=settings.embedding_dimension)
    return LocalEmbeddingClient(
        base_url=settings.local_embedding_base_url,
        model=settings.local_embedding_model,
        dimension=settings.embedding_dimension,
    )

