from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBasePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    source: str = Field(default="校内知识库", max_length=255)
    document_name: str | None = Field(default=None, max_length=255)
    document_path: str | None = Field(default=None, max_length=500)
    chunk_index: int | None = Field(default=None, ge=1)
    chunk_total: int | None = Field(default=None, ge=1)
    chunking_method: str | None = Field(default=None, max_length=50)


class KnowledgeCreate(KnowledgeBasePayload):
    pass


class KnowledgeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, max_length=255)
    document_name: str | None = Field(default=None, max_length=255)
    document_path: str | None = Field(default=None, max_length=500)
    chunk_index: int | None = Field(default=None, ge=1)
    chunk_total: int | None = Field(default=None, ge=1)
    chunking_method: str | None = Field(default=None, max_length=50)


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    category: str
    content: str
    source: str
    document_name: str | None = None
    document_path: str | None = None
    chunk_index: int | None = None
    chunk_total: int | None = None
    chunking_method: str | None = None
    embedding: list[float] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrievedKnowledge(BaseModel):
    id: int
    title: str
    category: str
    content: str
    source: str

    model_config = ConfigDict(from_attributes=True)


class DocumentImportResponse(BaseModel):
    filename: str
    stored_file_path: str
    imported_count: int
    items: list[KnowledgeResponse]
