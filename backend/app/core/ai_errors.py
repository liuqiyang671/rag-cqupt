class AIServiceError(RuntimeError):
    """User-facing error raised when an AI dependency cannot serve the request."""


class ModelProviderError(AIServiceError):
    """Raised when the configured chat model is unavailable or returns invalid data."""


class EmbeddingProviderError(AIServiceError):
    """Raised when the configured embedding model is unavailable or mismatched."""


class VectorSchemaError(AIServiceError):
    """Raised when pgvector schema does not match the configured embedding dimension."""
